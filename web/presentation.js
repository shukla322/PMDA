'use strict';

const roleInfo = [
  ['Planner', 'Frames the research question', 'Proposes a bounded plan from the target, lead and budget.'],
  ['Formulator', 'Defines how candidates are scored', 'Uses the registered predictor, uncertainty and property rules.'],
  ['Executor', 'Prepares the approved run', 'Builds an inspectable configuration; the controller launches it.'],
  ['Analyser', 'Checks the evidence', 'Compares evaluated molecules with the stated success criteria.']
];
const home = el('section');
home.id = 'home-view';
home.hidden = true;
document.querySelector('main').append(home);
const homeButton = button('Overview', () => show('home'), 'nav');
homeButton.dataset.view = 'home';
document.querySelector('nav').prepend(homeButton);
const originalShow = show;
show = async function(view) {
  home.hidden = view !== 'home';
  if (view !== 'home') return originalShow(view);
  activeView = 'home';
  events?.close();
  for (const name of ['campaigns', 'detail', 'registries', 'admin']) $('#'+name+'-view').hidden = true;
  $$('[data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  $('#breadcrumb').textContent = 'PMDA / OVERVIEW';
  await renderHome();
};
const originalEnter = enter;
enter = async function() { await originalEnter(); await show('home'); };

function makeIcon(type) {
  const span = el('span', undefined, 'action-icon');
  span.setAttribute('aria-hidden', 'true');
  span.textContent = type === 'example' ? '01' : type === 'test' ? '02' : '03';
  return span;
}
async function openReference(targetTab = 'portfolio') {
  const available = projects.find(p => p.id === 'stage7');
  if (!available) throw new Error('The completed reference experiment is not available to this account.');
  project = available.id;
  $('#project').value = project;
  const rows = await api('/projects/stage7/campaigns');
  if (!rows.length) throw new Error('The completed reference experiment is unavailable.');
  await openCampaign(rows[0].id);
  tab = targetTab;
  $$('.tabs [data-tab]').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  await renderTab();
}
async function startQuickTest() {
  project = 'workspace';
  $('#project').value = project;
  await show('campaigns');
  $('#new-form [name="candidates"]').value = '4';
  $('#new-dialog').showModal();
}
async function renderHome() {
  clear(home);
  const hero = el('section', undefined, 'product-hero');
  const copy = el('div', undefined, 'hero-copy');
  copy.append(el('div', 'PHARMA MOLECULAR DESIGN AGENT', 'eyebrow'), el('h1', 'Generate molecules.\\nUnderstand every decision.'), el('p', 'PMDA coordinates four constrained AI roles with a deterministic controller to generate and evaluate EGFR analogues on a local CPU.'));
  const status = el('div', undefined, 'hero-status');
  status.append(el('span', 'LOCAL', 'status-pill'), el('span', 'No paid APIs'), el('span', 'Human approval gates'));
  copy.append(status);
  const result = el('aside', undefined, 'reference-result');
  result.append(el('div', 'COMPLETED REFERENCE RUN', 'eyebrow'), el('strong', '3'), el('h2', 'prioritized candidates'), el('p', 'from 112 evaluated rows across a documented three-job EGFR campaign'), button('View candidate portfolio', () => openReference('portfolio'), 'quiet'));
  hero.append(copy, result);
  home.append(hero);
  const heading = el('div', undefined, 'section-heading');
  heading.append(el('h2', 'What would you like to do?'), el('p', 'Start with the completed example. It is the fastest way to understand the system without running computation.'));
  home.append(heading);
  const actions = el('div', undefined, 'action-grid');
  const choices = [
    ['example', 'Explore the completed example', 'See three prioritized molecules, prediction intervals and the recorded outcome.', 'No computation', () => openReference('portfolio')],
    ['test', 'Run a four-molecule test', 'Create a small experiment and approve each stage of the workflow yourself.', 'Uses local CPU', startQuickTest],
    ['agents', 'Inspect the agent workflow', 'See what each agent received, produced and was allowed to decide.', 'Recorded evidence', () => openReference('orchestration')]
  ];
  for (const [icon, title, body, meta, fn] of choices) {
    const card = button('', fn, 'action-card');
    card.append(makeIcon(icon), el('span', title, 'action-title'), el('span', body, 'action-description'), el('span', meta+' →', 'action-meta'));
    actions.append(card);
  }
  home.append(actions);
  const flow = el('section', undefined, 'workflow-summary');
  const flowHead = el('div');
  flowHead.append(el('div', 'HOW IT WORKS', 'eyebrow'), el('h2', 'Four specialists, one governed path'), el('p', 'The language model advises. Code controls state, budgets, approvals and execution.'));
  const stages = el('div', undefined, 'workflow-track');
  roleInfo.forEach(([name, title], index) => {
    const item = el('div', undefined, 'workflow-node');
    item.append(el('span', String(index+1).padStart(2, '0')), el('strong', name), el('small', title));
    stages.append(item);
  });
  flow.append(flowHead, stages);
  home.append(flow);
  const facts = el('section', undefined, 'fact-strip');
  for (const [value, label] of [['777', 'curated EGFR records'], ['4', 'specialist roles'], ['10', 'pilot benchmark runs'], ['3', 'reference candidates']]) {
    const item = el('div'); item.append(el('strong', value), el('span', label)); facts.append(item);
  }
  home.append(facts);
  const scope = el('details', undefined, 'about-project');
  scope.append(el('summary', 'About this BTech research prototype'));
  const body = el('div', undefined, 'about-grid');
  body.append(simpleInfo('Built here', 'State controller, role contracts, approvals, evidence trail, EGFR scoring integration and this portal.'), simpleInfo('Scientific stack', 'ChEMBL data, RDKit descriptors, a qualified random-forest baseline and REINVENT/Mol2Mol generation.'), simpleInfo('Honest boundary', 'The outputs are computational priorities. They are not experimental potency, safety or drug candidates.'));
  scope.append(body);
  home.append(scope);
}
function simpleInfo(title, text) { const item = el('div'); item.append(el('h3', title), el('p', text)); return item; }

const orchestrationButton = button('Agent workflow', async () => {
  tab = 'orchestration';
  $$('.tabs [data-tab]').forEach(b => b.classList.toggle('active', b === orchestrationButton));
  await renderTab();
});
orchestrationButton.dataset.tab = 'orchestration';
orchestrationButton.setAttribute('role', 'tab');
$('.tabs [data-tab="overview"]').after(orchestrationButton);
const portfolioButton = button('Prioritized molecules', async () => {
  tab = 'portfolio';
  $$('.tabs [data-tab]').forEach(b => b.classList.toggle('active', b === portfolioButton));
  await renderTab();
});
portfolioButton.dataset.tab = 'portfolio';
portfolioButton.setAttribute('role', 'tab');
$('.tabs [data-tab="candidates"]').before(portfolioButton);
const advancedButton = button('More evidence', () => {
  const tabs = $('.tabs');
  const open = tabs.classList.toggle('show-advanced');
  advancedButton.textContent = open ? 'Less evidence' : 'More evidence';
}, 'tab-more');
advancedButton.type = 'button';
$('.tabs').append(advancedButton);
const baseRenderTab = renderTab;
renderTab = async function() {
  if (tab === 'orchestration') { clear($('#tab-content')); await renderOrchestration(); }
  else if (tab === 'portfolio') { clear($('#tab-content')); await renderPortfolio(); }
  else await baseRenderTab();
};
async function renderPortfolio() {
  const data = await api(base()+'/portfolio');
  const intro = el('div', undefined, 'result-intro');
  intro.append(el('div', 'COMPUTATIONAL OUTCOME', 'eyebrow'), el('h2', data.rows.length+' molecules met every configured rule'), el('p', 'Predicted activity is shown with uncertainty and model-domain status. These molecules require experimental validation.'));
  $('#tab-content').append(intro);
  if (!data.rows.length) return;
  const cards = el('div', undefined, 'portfolio-grid');
  data.rows.forEach((row, index) => {
    const activity = row.activity || {};
    const card = el('article', undefined, 'molecule-card');
    const img = el('img'); img.src = '/api/v1'+base()+'/molecule/'+row.row; img.alt = 'Structure of prioritized molecule '+(index+1);
    const top = el('div', undefined, 'molecule-top');
    top.append(el('span', 'CANDIDATE '+String(index+1).padStart(2, '0'), 'eyebrow'), el('span', activity.in_domain ? 'Within model domain' : 'Outside model domain', 'domain-pill '+(activity.in_domain ? 'good' : 'warn')));
    const score = el('div', undefined, 'prediction');
    score.append(el('strong', fmt(activity.value)), el('span', 'predicted pIC50'), el('small', fmt(activity.lower)+' – '+fmt(activity.upper)+' interval'));
    const more = el('details'); more.append(el('summary', 'Inspect properties and provenance'), el('pre', JSON.stringify({smiles: row.canonical_smiles, activity, descriptors: row.descriptors, alerts: row.alerts, rejection_reasons: row.rejection_reasons}, null, 2)));
    card.append(top, img, score, el('code', row.canonical_smiles), more);
    cards.append(card);
  });
  $('#tab-content').append(cards);
}
async function renderOrchestration() {
  const data = await api(base()+'/orchestration');
  const intro = el('div', undefined, 'result-intro');
  intro.append(el('div', 'RECORDED WORKFLOW', 'eyebrow'), el('h2', 'How the agents contributed'), el('p', 'Select a role to inspect its responsibility and recorded run evidence.'));
  $('#tab-content').append(intro);
  const layout = el('div', undefined, 'orchestration-layout');
  const rail = el('div', undefined, 'role-rail');
  const inspector = el('section', undefined, 'role-inspector');
  function inspect(index) {
    const [name, title, description] = roleInfo[index];
    const roleKey = name === 'Executor' ? 'executor' : name.toLowerCase();
    const record = data.roles.find(r => r.role === roleKey);
    clear(inspector);
    inspector.append(el('div', 'ROLE '+String(index+1).padStart(2, '0'), 'eyebrow'), el('h2', name), el('h3', title), el('p', description));
    if (record) {
      const metrics = el('div', undefined, 'role-metrics');
      metrics.append(simpleMetric(record.attempts.length, 'attempts'), simpleMetric(record.tokens, 'tokens'), simpleMetric(record.seconds.toFixed(1)+'s', 'elapsed'));
      inspector.append(metrics);
      const evidence = el('details'); evidence.append(el('summary', 'View the actual context and responses'), el('pre', JSON.stringify({context: record.context?.context, provider: record.context?.provider, attempts: record.attempts}, null, 2)));
      inspector.append(evidence);
    } else inspector.append(el('p', 'This role did not record evidence in the current campaign.'));
    [...rail.children].forEach((b, i) => b.classList.toggle('selected', i === index));
  }
  roleInfo.forEach(([name, title], index) => {
    const b = button('', () => inspect(index), 'role-button');
    b.append(el('span', String(index+1).padStart(2, '0')), el('strong', name), el('small', title));
    rail.append(b);
  });
  layout.append(rail, inspector);
  $('#tab-content').append(layout);
  inspect(0);
}
function simpleMetric(value, label) { const item = el('div'); item.append(el('strong', value), el('span', label)); return item; }
const baseOverview = overview;
overview = async function() {
  await baseOverview();
  const state = detail.campaign.state;
  const steps = [
    ['Plan', ['DRAFT','PLANNING','AWAITING_PLAN_APPROVAL']],
    ['Scoring', ['FORMULATING','AWAITING_SCORE_APPROVAL']],
    ['Run setup', ['CONFIGURING','AWAITING_LAUNCH_APPROVAL','QUEUED']],
    ['Generate', ['RUNNING']],
    ['Review result', ['EVALUATING','ANALYSING','COMPLETED','FAILED','CANCELLED']]
  ];
  let current = steps.findIndex(([, states]) => states.includes(state));
  if (current < 0) current = 0;
  const progress = el('section', undefined, 'stage-progress');
  progress.append(el('div', 'CURRENT WORKFLOW', 'eyebrow'));
  const track = el('div', undefined, 'stage-track');
  steps.forEach(([name], index) => {
    const item = el('div', undefined, 'stage '+(index < current ? 'done' : index === current ? 'current' : ''));
    item.append(el('span', index < current ? '✓' : String(index+1)), el('strong', name));
    track.append(item);
  });
  progress.append(track);
  $('#tab-content').prepend(progress);
  const raw = $('#tab-content .panel pre');
  if (raw && !raw.closest('details')) {
    const disclosure = el('details', undefined, 'artifact-details');
    disclosure.append(el('summary', 'Inspect the complete approval artifact'));
    raw.replaceWith(disclosure);
    disclosure.append(raw);
  }
};
if (session && activeView === 'campaigns') show('home').catch(e => message(e.message, true));
