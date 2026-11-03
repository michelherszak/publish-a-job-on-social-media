import {renderToStaticMarkup,renderToString} from 'react-dom/server';
import {JobPortal,type JobResult,type JobFilters} from './JobPortal';
import {ApplyPage,type JobPage} from './Apply';
import {JobDescription} from './JobDescription';
export function renderDirectory(data:JobResult,filters:JobFilters,offset:number){return renderToString(<JobPortal initialResult={data} initialFilters={filters} initialOffset={offset}/>);}
export function renderJob(data:JobPage,id:string){return renderToString(<ApplyPage portal initialPage={data} campaignId={id}/>);}
export function jobDescription(text:string){return renderToStaticMarkup(<JobDescription text={text}/>);}
