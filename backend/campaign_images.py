"""Private, campaign-scoped photos and deterministic feed/story crops. No provider calls."""
import io
import json
import re
import time
import warnings

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import Response
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field
from typing import Annotated, Literal

MAX_UPLOAD = 10 * 1024 * 1024
MAX_IMAGES = 6
FORMATS = {'feed': (1080, 1350), 'story': (1080, 1920)}


class Crop(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    x: float = Field(default=0.5, ge=0, le=1)
    y: float = Field(default=0.5, ge=0, le=1)
    zoom: float = Field(default=1, ge=1, le=3)


class ImageEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: int = Field(gt=0)
    revision: int = Field(ge=1)
    feed: Crop
    story: Crop


def schema(conn):
    conn.executescript('''CREATE TABLE IF NOT EXISTS campaign_images (
        id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        name TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
        original BLOB NOT NULL, feed BLOB NOT NULL, story BLOB NOT NULL,
        crops TEXT NOT NULL, selected INTEGER NOT NULL DEFAULT 0,
        revision INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS campaign_images_project ON campaign_images(project_id);
        CREATE UNIQUE INDEX IF NOT EXISTS campaign_images_selected ON campaign_images(project_id) WHERE selected=1;
    ''')
    if 'image_revision' not in {r['name'] for r in conn.execute('PRAGMA table_info(projects)')}:
        conn.execute('ALTER TABLE projects ADD COLUMN image_revision INTEGER NOT NULL DEFAULT 0')


def serialize(row):
    crops = json.loads(row['crops'])
    return {k: row[k] for k in ('id', 'name', 'width', 'height', 'revision')} | {'selected': bool(row['selected']), **crops}


def listing(conn, project_id):
    return {'images': [serialize(r) for r in conn.execute('SELECT id,name,width,height,revision,selected,crops FROM campaign_images WHERE project_id=? ORDER BY id', (project_id,))]}


def jpeg(image):
    out = io.BytesIO()
    image.save(out, 'JPEG', quality=90, optimize=True)
    return out.getvalue()


def crop_image(image, crop, format):
    width, height = FORMATS[format]
    ratio = width / height
    cw = min(image.width, image.height * ratio) / crop.zoom
    ch = cw / ratio
    left = (image.width - cw) * crop.x
    top = (image.height - ch) * crop.y
    return jpeg(image.crop((round(left), round(top), round(left + cw), round(top + ch))).resize((width, height), Image.Resampling.LANCZOS))


def prepare(data):
    if not data or len(data) > MAX_UPLOAD:
        raise HTTPException(413, 'Bild zu groß oder leer (maximal 10 MiB).')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {'JPEG', 'PNG', 'WEBP'} or getattr(source, 'is_animated', False):
                    raise ValueError()
                if source.width * source.height > 16_000_000 or min(source.size) < 100:
                    raise ValueError()
                source.load()
                oriented = ImageOps.exif_transpose(source)
                rgba = oriented.convert('RGBA')
                image = Image.new('RGB', rgba.size, 'white')
                image.paste(rgba, mask=rgba.getchannel('A'))
                image.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
                # New RGB pixels strip EXIF/GPS, profiles and embedded metadata.
                clean = Image.new('RGB', image.size)
                clean.paste(image)
                return clean
    except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise HTTPException(422, 'Bitte ein einzelnes JPG-, PNG- oder WebP-Bild mit mindestens 100 Pixeln je Seite und höchstens 16 Millionen Bildpunkten hochladen.') from None


def edit(conn, project, body):
    row = conn.execute('SELECT * FROM campaign_images WHERE id=? AND project_id=? AND selected=1', (body.id, project['id'])).fetchone()
    if not row:
        raise HTTPException(404, 'Not found')
    if row['revision'] != body.revision:
        raise HTTPException(409, 'Das Bild wurde inzwischen geändert. Bitte die Kampagne neu öffnen und den Ausschnitt erneut prüfen.')
    with Image.open(io.BytesIO(row['original'])) as image:
        feed = crop_image(image, body.feed, 'feed')
        story = crop_image(image, body.story, 'story')
    conn.execute('UPDATE campaign_images SET feed=?,story=?,crops=?,revision=revision+1 WHERE id=?', (feed, story, json.dumps({'feed': body.feed.model_dump(), 'story': body.story.model_dump()}), body.id))


def export(conn, project_id):
    row = conn.execute('SELECT * FROM campaign_images WHERE project_id=? AND selected=1', (project_id,)).fetchone()
    if not row:
        return {}
    return {'images/feed-4x5.jpg': row['feed'], 'images/story-9x16.jpg': row['story'],
            'images/selection.json': json.dumps(serialize(row), ensure_ascii=False, indent=2)}


def install(app, db, current_user, require, project_row, changed):
    def writable(conn, project_id, user):
        require(user, 'campaigns:write')
        project = project_row(conn, project_id, user)
        try:
            from . import recruiting
        except ImportError:
            import recruiting
        recruiting.ensure_open(conn, project_id)
        if project['status'] == 'Live':
            raise HTTPException(409, 'Live campaigns cannot be edited')
        return project

    @app.get('/campaigns/{project_id}/images')
    def images(project_id: int, user=Depends(current_user)):
        require(user, 'campaigns:read')
        with db(user) as conn:
            project_row(conn, project_id, user)
            return listing(conn, project_id)

    @app.get('/campaigns/{project_id}/images/{image_id}/{format}')
    def image_file(project_id: int, image_id: int, format: Literal['original', 'feed', 'story'], user=Depends(current_user)):
        require(user, 'campaigns:read')
        with db(user) as conn:
            project_row(conn, project_id, user)
            row = conn.execute('SELECT * FROM campaign_images WHERE project_id=? AND id=?', (project_id, image_id)).fetchone()
            if not row:
                raise HTTPException(404, 'Not found')
            return Response(row[format], media_type='image/jpeg', headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})

    @app.post('/campaigns/{project_id}/images', status_code=201)
    async def upload(project_id: int, request: Request, name: Annotated[str, Query(max_length=160)] = 'Foto', user=Depends(current_user)):
        # Check tenant, subscription and workflow before decoding an image.
        with db(user) as conn:
            writable(conn, project_id, user)
        image = await run_in_threadpool(prepare, await request.body())
        center = Crop()
        original = await run_in_threadpool(jpeg, image)
        feed = await run_in_threadpool(crop_image, image, center, 'feed')
        story = await run_in_threadpool(crop_image, image, center, 'story')
        safe_name = re.split(r'[/\\]', name)[-1].strip()[:160] or 'Foto'
        with db(user) as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = writable(conn, project_id, user)
            if conn.execute('SELECT COUNT(*) FROM campaign_images WHERE project_id=?', (project_id,)).fetchone()[0] >= MAX_IMAGES:
                raise HTTPException(409, 'Pro Kampagne sind höchstens sechs Fotos möglich.')
            selected = not conn.execute('SELECT 1 FROM campaign_images WHERE project_id=? AND selected=1', (project_id,)).fetchone()
            conn.execute('INSERT INTO campaign_images(project_id,name,width,height,original,feed,story,crops,selected,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)', (project_id, safe_name, image.width, image.height, original, feed, story, json.dumps({'feed':center.model_dump(),'story':center.model_dump()}), int(selected), int(time.time())))
            changed(conn, project, user, 'image_uploaded', 'Kampagnenfoto hinzugefügt')
            return listing(conn, project_id)

    @app.post('/campaigns/{project_id}/images/{image_id}/select')
    def select(project_id: int, image_id: int, user=Depends(current_user)):
        with db(user) as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = writable(conn, project_id, user)
            row = conn.execute('SELECT selected FROM campaign_images WHERE project_id=? AND id=?', (project_id, image_id)).fetchone()
            if not row:
                raise HTTPException(404, 'Not found')
            if not row['selected']:
                conn.execute('UPDATE campaign_images SET selected=0 WHERE project_id=?', (project_id,))
                conn.execute('UPDATE campaign_images SET selected=1 WHERE id=?', (image_id,))
                changed(conn, project, user, 'image_selected', 'Kampagnenmotiv ausgewählt')
            return listing(conn, project_id)

    @app.delete('/campaigns/{project_id}/images/{image_id}')
    def remove(project_id: int, image_id: int, user=Depends(current_user)):
        with db(user) as conn:
            conn.execute('BEGIN IMMEDIATE')
            project = writable(conn, project_id, user)
            row = conn.execute('SELECT selected FROM campaign_images WHERE project_id=? AND id=?', (project_id, image_id)).fetchone()
            if not row:
                raise HTTPException(404, 'Not found')
            conn.execute('DELETE FROM campaign_images WHERE id=?', (image_id,))
            if row['selected']:
                conn.execute('UPDATE campaign_images SET selected=1 WHERE id=(SELECT id FROM campaign_images WHERE project_id=? ORDER BY id LIMIT 1)', (project_id,))
            changed(conn, project, user, 'image_removed', 'Kampagnenfoto entfernt')
            return listing(conn, project_id)
