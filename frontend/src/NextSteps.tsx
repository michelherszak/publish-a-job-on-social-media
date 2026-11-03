import { ChevronRight, CircleCheck, ClipboardCheck, FileText, MessageSquare, Clock3 } from 'lucide-react';
import { t } from './i18n';
import './next-steps.css';

type Campaign = { id: number; organization_id: number; role: string; status: 'Draft' | 'Review' | 'Live'; generated: Record<string, string>; change_request: string; updated_at: number };
type Kind = 'feedback' | 'approval' | 'draft' | 'brief';
type Step<T> = { campaign: T; kind: Kind };
const priority: Record<Kind, number> = { feedback: 0, approval: 1, draft: 2, brief: 3 };

export function getNextSteps<T extends Campaign>(campaigns: T[], canWrite: boolean, canApprove: boolean): Step<T>[] {
  const steps: Step<T>[] = [];
  for (const campaign of campaigns) {
    // A submitted campaign can retain old feedback; its current status takes precedence.
    if (campaign.status === 'Review' && canApprove) steps.push({ campaign, kind: 'approval' });
    else if (campaign.status === 'Draft' && canWrite) {
      const kind = campaign.change_request.trim() ? 'feedback'
        : Object.values(campaign.generated).some(text => text.trim()) ? 'draft' : 'brief';
      steps.push({ campaign, kind });
    }
  }
  return steps.sort((a, b) => priority[a.kind] - priority[b.kind] || a.campaign.updated_at - b.campaign.updated_at || a.campaign.id - b.campaign.id);
}

const labels = {
  feedback: t('Feedback bearbeiten'), approval: t('Freigabe ausstehend'),
  draft: t('Entwurf prüfen'), brief: t('Briefing fortsetzen'),
};
const icons = { feedback: MessageSquare, approval: Clock3, draft: ClipboardCheck, brief: FileText };
type Props<T extends Campaign> = { campaigns: T[]; canWrite: boolean; canApprove: boolean; orgName: (id: number) => string; onOpen: (campaign: T) => void };

export function NextSteps<T extends Campaign>({ campaigns, canWrite, canApprove, orgName, onOpen }: Props<T>) {
  const steps = getNextSteps(campaigns, canWrite, canApprove);
  function row({ campaign, kind }: Step<T>) {
    const Icon = icons[kind];
    return <button type="button" key={campaign.id} className="next-step" onClick={() => onOpen(campaign)} aria-label={`${labels[kind]} · ${campaign.role} · ${orgName(campaign.organization_id)}`}>
      <span className={`next-step-icon next-step-${kind}`} aria-hidden="true"><Icon size={17}/></span>
      <span className="next-step-copy"><strong>{labels[kind]}</strong><span>{campaign.role}</span><small>{orgName(campaign.organization_id)}</small></span>
      <ChevronRight size={16} aria-hidden="true"/>
    </button>;
  }
  return <section className="next-steps" aria-labelledby="next-steps-heading">
    <header className="next-steps-heading"><h2 id="next-steps-heading">{t('Nächste Schritte')}</h2>{steps.length > 0 && <span className="next-steps-count" aria-label={steps.length === 1 ? t('Ein offener Schritt') : t('{count} offene Schritte', { count: steps.length })}>{steps.length}</span>}</header>
    {steps.length ? <>
      <div className="next-steps-list">{steps.slice(0, 3).map(row)}</div>
      {steps.length > 3 && <details className="next-steps-more"><summary>{steps.length === 4 ? t('Ein weiterer Schritt') : t('{count} weitere Schritte', { count: steps.length - 3 })}</summary><div className="next-steps-list">{steps.slice(3).map(row)}</div></details>}
    </> : <div className="next-steps-empty"><CircleCheck size={22} aria-hidden="true"/><div><strong>{t('Alles erledigt')}</strong><p>{t('Für dich sind gerade keine Aufgaben offen.')}</p></div></div>}
  </section>;
}
