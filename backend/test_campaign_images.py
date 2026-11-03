"""Offline photos, permissions, review consistency and atomic campaign exports."""
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
from backend import main, campaign_images, auth
from backend.test_support import BrowserClient, session_headers


class CampaignImageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.patches = [patch.object(main, 'DB', root/'db'), patch.object(main, 'DEMO_DB', root/'demo'), patch.object(main, 'CREDENTIALS', root/'credentials'), patch.object(auth, 'OUTBOX', root/'outbox'), patch.object(auth, 'deliver_message'), patch.dict(os.environ, {'MH_ENV':'development','MH_MAIL_MODE':'local'})]
        for item in self.patches: item.start()
        main.init_db()
        self.client = BrowserClient(main.app)
        self.passwords = dict(line.split() for line in main.CREDENTIALS.read_text().splitlines()[1:])
        self.a = self.login('admin@mueller.local')
        self.b = self.login('admin@autohaus.local')
        self.admin = self.login('admin@flh.local')
        self.org = self.client.get('/organizations', headers=self.a).json()[0]['id']
        self.project = self.client.post('/campaigns', headers=self.a, json={'organization_id':self.org,'briefing':{'role':'Image fixture','location':'Berlin','channels':['Instagram','Meta']}}).json()['id']
        self.path = f'/campaigns/{self.project}'
        photo = Image.new('RGB', (1200, 1600), 'red')
        ImageDraw.Draw(photo).rectangle((600,0,1200,1600),fill='blue')
        output = io.BytesIO()
        exif = Image.Exif();exif[270] = 'private fixture metadata'
        photo.save(output,'JPEG',exif=exif)
        self.photo = output.getvalue()

    def tearDown(self):
        self.client.close()
        for item in reversed(self.patches): item.stop()
        self.tmp.cleanup()

    def login(self, email):
        response=self.client.post('/auth/login',json={'email':email,'password':self.passwords[email]})
        self.assertEqual(response.status_code,200,response.text)
        headers=session_headers(self.client);self.client.cookies.clear();return headers

    def upload(self, headers=None, photo=None):
        return self.client.post(self.path+'/images?name=fixture.jpg',headers=headers or self.a,content=self.photo if photo is None else photo)

    def first(self):
        result=self.upload();self.assertEqual(result.status_code,201,result.text);return result.json()['images'][-1]

    def save(self, image, **changes):
        body={'image_edit':{k:image[k] for k in ('id','revision','feed','story')},**changes}
        return self.client.patch(self.path,headers=self.a,json=body)

    def test_upload_cleans_metadata_and_exports_selected_jpg_formats(self):
        row=self.first()
        self.assertTrue(row['selected'])
        original=self.client.get(f"{self.path}/images/{row['id']}/original",headers=self.a)
        self.assertIn('no-store',original.headers['cache-control'])
        with Image.open(io.BytesIO(original.content)) as image:self.assertFalse(image.getexif())
        self.assertNotIn(b'private fixture metadata',original.content)
        export=self.client.get(self.path+'/export',headers=self.a)
        with zipfile.ZipFile(io.BytesIO(export.content)) as package:
            for name,size in [('feed-4x5.jpg',(1080,1350)),('story-9x16.jpg',(1080,1920))]:
                with Image.open(io.BytesIO(package.read('images/'+name))) as image:self.assertEqual(image.size,size)
            self.assertEqual(json.loads(package.read('images/selection.json'))['id'],row['id'])

    def test_crop_and_text_save_are_atomic_and_preview_geometry_matches(self):
        row=self.first();row['story']['x']=1;row['story']['zoom']=2
        saved=self.save(row,generated={'social':'Edited caption','meta':'Edited ad','jobAd':'Shared description'})
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertEqual(saved.json()['generated']['social'],'Edited caption')
        updated=self.client.get(self.path+'/images',headers=self.a).json()['images'][0]
        self.assertEqual(updated['story'],row['story'])
        output=self.client.get(f"{self.path}/images/{row['id']}/story",headers=self.a)
        with Image.open(io.BytesIO(output.content)) as image:
            red,green,blue=image.getpixel((540,960));self.assertGreater(blue,200);self.assertLess(red,30)
        conflict=self.save(row,generated={'social':'Must not overwrite'})
        self.assertEqual(conflict.status_code,409)
        self.assertEqual(self.client.get(self.path,headers=self.a).json()['generated']['social'],'Edited caption')

    def test_photos_are_private_and_foreign_ids_cannot_be_selected(self):
        row=self.first()
        self.assertEqual(self.client.get(self.path+'/images').status_code,401)
        for route in [self.path+'/images',f"{self.path}/images/{row['id']}/feed",self.path+'/export']:
            self.assertEqual(self.client.get(route,headers=self.b).status_code,404)
        self.assertEqual(self.upload(self.b).status_code,404)
        self.assertEqual(self.client.post(f"{self.path}/images/{row['id']}/select",headers=self.b).status_code,404)
        self.assertEqual(self.client.delete(f"{self.path}/images/{row['id']}",headers=self.b).status_code,404)
        other=self.client.post('/campaigns',headers=self.a,json={'organization_id':self.org,'briefing':{'role':'Other fixture','location':'Berlin'}}).json()['id']
        self.assertEqual(self.client.post(f"/campaigns/{other}/images/{row['id']}/select",headers=self.a).status_code,404)

    def test_client_read_only_and_paid_subscription_write_gate(self):
        row=self.first()
        self.client.post(self.path+'/generate',headers=self.a)
        self.client.patch(self.path,headers=self.a,json={'status':'Review','image_revision':1})
        with main.db() as conn:
            conn.execute("INSERT INTO users(email,name,password_hash,role,organization_id) VALUES(?,?,?,?,?)",('image-client@example.test','Fixture',main.password_hash('fixture-long-password'),'kunde',self.org))
        self.passwords['image-client@example.test']='fixture-long-password'
        client=self.login('image-client@example.test')
        self.assertEqual(self.client.get(f"{self.path}/images/{row['id']}/feed",headers=client).status_code,200)
        self.assertEqual(self.upload(client).status_code,403)
        self.assertEqual(self.client.delete(f"{self.path}/images/{row['id']}",headers=client).status_code,403)
        with main.db() as conn:
            conn.execute("INSERT INTO billing_accounts(organization_id,mode,status,country) VALUES(?,'test','unpaid','DE')",(self.org,))
        self.assertEqual(self.upload().status_code,402)
        self.assertEqual(self.save(row).status_code,402)

    def test_image_changes_reset_review_and_stale_approval_is_rejected(self):
        row=self.first();self.client.post(self.path+'/generate',headers=self.a)
        self.assertEqual(self.client.patch(self.path,headers=self.a,json={'status':'Review','image_revision':1}).status_code,200)
        row['feed']['zoom']=1.1
        result=self.save(row);self.assertEqual(result.status_code,200,result.text);self.assertEqual(result.json()['status'],'Draft')
        self.assertEqual(self.client.patch(self.path,headers=self.a,json={'status':'Review','image_revision':1}).status_code,409)
        self.assertEqual(self.client.patch(self.path,headers=self.a,json={'status':'Review','image_revision':2}).status_code,200)
        self.assertEqual(self.client.patch(self.path,headers=self.a,json={'status':'Live','image_revision':1}).status_code,409)
        self.assertEqual(self.client.patch(self.path,headers=self.a,json={'status':'Live','image_revision':2}).status_code,200)
        self.assertEqual(self.upload().status_code,409)
        self.assertEqual(self.save(row).status_code,409)
        self.assertEqual(self.client.delete(f"{self.path}/images/{row['id']}",headers=self.a).status_code,409)

    def test_upload_rejects_unsupported_broken_animated_and_oversize_files(self):
        self.assertEqual(self.upload(photo=b'<svg xmlns="http://www.w3.org/2000/svg"/>').status_code,422)
        self.assertEqual(self.upload(photo=b'broken photo').status_code,422)
        self.assertEqual(self.upload(photo=b'').status_code,413)
        self.assertEqual(self.upload(photo=b'x'*(campaign_images.MAX_UPLOAD+1)).status_code,413)
        animated=io.BytesIO();a=Image.new('RGB',(150,150),'red');b=Image.new('RGB',(150,150),'blue');a.save(animated,'WEBP',save_all=True,append_images=[b])
        self.assertEqual(self.upload(photo=animated.getvalue()).status_code,422)
        with patch.object(campaign_images.Image,'open') as opened:
            source=opened.return_value.__enter__.return_value;source.format='PNG';source.width=5000;source.height=5000;source.size=(5000,5000);source.is_animated=False
            self.assertEqual(self.upload().status_code,422);source.load.assert_not_called()
        self.assertEqual(self.client.get(self.path+'/images',headers=self.a).json()['images'],[])
        # The larger limit applies only to photo upload, not normal campaign JSON.
        self.assertEqual(self.client.patch(self.path,headers=self.a,content=b'x'*(1024*1024+1)).status_code,413)

    def test_crop_bounds_and_image_count_limit_keep_existing_assets(self):
        row=self.first()
        for value in (-0.1,1.1):
            row['feed']['x']=value;self.assertEqual(self.save(row).status_code,422)
        row['feed']['x']=0.5;row['story']['zoom']=0.5;self.assertEqual(self.save(row).status_code,422)
        with patch.object(campaign_images,'MAX_IMAGES',1):self.assertEqual(self.upload().status_code,409)
        self.assertEqual(len(self.client.get(self.path+'/images',headers=self.a).json()['images']),1)

    def test_select_remove_demo_isolation_and_cascade_cleanup(self):
        first=self.first();second=self.first()
        self.assertFalse(second['selected'])
        selected=self.client.post(f"{self.path}/images/{second['id']}/select",headers=self.a).json()['images']
        self.assertEqual([r['id'] for r in selected if r['selected']],[second['id']])
        self.client.post('/demo/context',headers=self.admin,json={'role':'firmen_admin','organization_id':self.org})
        self.client.delete(f"{self.path}/images/{second['id']}",headers=self.admin)
        self.assertEqual(len(self.client.get(self.path+'/images',headers=self.admin).json()['images']),1)
        self.assertEqual(len(self.client.get(self.path+'/images',headers=self.a).json()['images']),2)
        removed=self.client.delete(f"{self.path}/images/{second['id']}",headers=self.a).json()['images']
        self.assertTrue(removed[0]['selected']);self.assertEqual(removed[0]['id'],first['id'])
        with main.db() as conn:
            conn.execute('DELETE FROM activity WHERE project_id=?',(self.project,));conn.execute('DELETE FROM campaign_history WHERE project_id=?',(self.project,));conn.execute('DELETE FROM projects WHERE id=?',(self.project,))
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM campaign_images WHERE project_id=?',(self.project,)).fetchone()[0],0)
