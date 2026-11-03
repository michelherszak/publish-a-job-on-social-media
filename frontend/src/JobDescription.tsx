// Plain text/Markdown only. React escapes all employer content; no raw HTML is accepted.
export function JobDescription({text}:{text:string}) {
  return <article className="apply-copy">{text.trim().split(/\n{2,}/).map((block,index)=>{
    const lines=block.split('\n');
    const heading=lines[0].match(/^#{1,6}\s+(.+)$/);
    const body=(heading?lines.slice(1):lines).filter(line=>line.trim());
    const clean=(value:string)=>value.replace(/\*\*/g,'');
    const list=body.length>0&&body.every(line=>/^\s*[-*•]\s+/.test(line));
    return <section key={index}>{heading&&<h2>{clean(heading[1])}</h2>}{list?<ul>{body.map((line,i)=><li key={i}>{clean(line.replace(/^\s*[-*•]\s+/,''))}</li>)}</ul>:body.length>0&&<p>{clean(body.join('\n'))}</p>}</section>;
  })}</article>;
}
