(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) {
    root.LTGCapitalDiagnostic = api;
    if (root.document) api.boot();
  }
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';

  var VERSION = '2026-07-28.1';
  var CONSENT_VERSION = 'capital-diagnostic-2026-07-28';
  var SMS_DISCLOSURE_VERSION = 'sms-program-2026-07-28';

  var TRACKS = {
    construction: {
      label: 'Development stack review',
      eyebrow: 'For owners, sponsors, and developers',
      headline: 'Can the capital stack carry the project through stabilization?',
      intro: 'Pressure-test the financing, equity, timing, and execution assumptions behind a development or major renovation.',
      pressure: 'Budget, timing, recourse, and the path from construction through stabilization.',
      compare: 'Construction debt, whole-loan or private-credit execution, and senior-plus-subordinate structures.',
      prepare: 'Sources and uses, budget, schedule, equity evidence, entitlement status, and stabilization assumptions.'
    },
    refinance: {
      label: 'Refinance readiness review',
      eyebrow: 'A private capital diagnostic',
      headline: 'How exposed is your next financing to the same market pressure?',
      intro: 'Test maturity timing, proceeds, operating evidence, and the range of structures worth comparing before lender outreach.',
      pressure: 'Debt service, proceeds, maturity timing, and confidence in the operating story.',
      compare: 'Bank, life-company, agency, CMBS, bridge, and structured-debt alternatives where relevant.',
      prepare: 'Current debt terms, rent roll, trailing operations, maturity date, business plan, and requested proceeds.'
    },
    recapitalization: {
      label: 'Capital stack pressure test',
      eyebrow: 'For complex or time-sensitive situations',
      headline: 'Where is pressure building in your capital stack?',
      intro: 'Clarify the refinancing gap, control questions, timing, and subordinate-capital options before the structure hardens.',
      pressure: 'Maturity risk, an equity gap, partner alignment, control rights, or a mismatch between the asset and existing debt.',
      compare: 'Senior refinancing, preferred equity, mezzanine capital, JV equity, and negotiated recapitalization paths.',
      prepare: 'Existing stack, maturity and extension rights, current value support, partner objectives, and required new capital.'
    },
    transaction: {
      label: 'Transaction financeability review',
      eyebrow: 'Before the basis becomes fixed',
      headline: 'Would the transaction finance at the basis you are considering?',
      intro: 'Test the capital requirement, closing window, business plan, and likely execution pressure before commitments are fixed.',
      pressure: 'Basis, closing timing, sponsor equity, transition risk, and the evidence supporting the exit.',
      compare: 'Acquisition debt, bridge financing, permanent debt, preferred equity, and JV structures where relevant.',
      prepare: 'Purchase price, sources and uses, closing schedule, operating information, business plan, and equity plan.'
    },
    operations: {
      label: 'NOI-to-proceeds review',
      eyebrow: 'Translate operations into capital',
      headline: 'How will the operating story translate into loan proceeds?',
      intro: 'Identify which leasing, occupancy, rollover, or income assumptions will matter most to the next capital decision.',
      pressure: 'The durability of NOI, lease rollover, tenant credit, occupancy, and the time required to stabilize.',
      compare: 'Permanent financing, bridge debt, structured capital, and a delayed process while operating evidence develops.',
      prepare: 'Rent roll, lease schedule, occupancy history, trailing operations, capital plan, and stabilization milestones.'
    },
    general: {
      label: 'Capital readiness review',
      eyebrow: 'A private 90-second diagnostic',
      headline: 'Pressure-test the capital plan behind your next move.',
      intro: 'Answer six focused questions and receive a concise view of the likely execution pressure and what to prepare next.',
      pressure: 'Structure, timing, operating evidence, sponsor objectives, and the fit between the asset and requested capital.',
      compare: 'Senior debt, bridge or structured debt, preferred or JV equity, and recapitalization alternatives.',
      prepare: 'A concise sources and uses, asset summary, operating evidence, timeline, and the decision the capital must solve.'
    }
  };

  var OUTCOMES = {
    ready_to_run: {
      title: 'Ready to run a focused process',
      description: 'The transaction appears defined enough to begin a disciplined capital review. The next advantage comes from presenting the case clearly and comparing executable structures on equal terms.',
      next: 'Confirm the financing request, prepare a concise capital package, and establish the decision criteria before outreach.'
    },
    structure_before_market: {
      title: 'Structure before market',
      description: 'The capital need is real, but one or more assumptions should be clarified before the market is approached. Resolving them first can improve comparability, credibility, and negotiating leverage.',
      next: 'Define the proceeds, timing, downside case, and acceptable trade-offs before selecting capital sources.'
    },
    capital_stack_pressure: {
      title: 'Capital-stack pressure is the central issue',
      description: 'The primary question is not simply whether capital is available. It is how new capital interacts with existing debt, partner economics, control, and a time-sensitive decision.',
      next: 'Map every layer of the current stack and compare the cost, control, and execution risk of each restructuring path.'
    },
    planning_window: {
      title: 'You are in the planning window',
      description: 'The transaction is early enough that decisions made now can materially improve later execution. This is the moment to identify evidence gaps and avoid fixing the structure too soon.',
      next: 'Set the target capital event, monitor the assumptions that can change proceeds, and prepare the information capital will eventually require.'
    },
    referral_profile: {
      title: 'A potentially valuable referral situation',
      description: 'The scenario can be framed for an efficient confidential review without placing the referral partner in the middle of the capital process.',
      next: 'Confirm the sponsor’s objective, timing, and permission to make an introduction.'
    },
    provider_profile: {
      title: 'Capital-provider profile captured',
      description: 'Your strategy can be matched more intelligently when a relevant sponsor mandate or market theme enters the Light Tower network.',
      next: 'Keep check size, geography, structure, and current deployment priorities current.'
    },
    reader_profile: {
      title: 'Your intelligence profile is set',
      description: 'Your interests can now inform which Light Tower research and market developments are most relevant to you.',
      next: 'Use the optional Insights permission below if you would like future editorial updates.'
    }
  };

  var QUESTION_BANK = {
    role: {
      id: 'role',
      eyebrow: 'Your position',
      question: 'Which best describes you?',
      options: [
        ['sponsor_owner', 'Owner or sponsor', 'I control or represent the ownership of an asset.'],
        ['developer', 'Developer', 'I am evaluating or executing a development plan.'],
        ['referral', 'Advisor or referral partner', 'I may introduce a sponsor, owner, or transaction.'],
        ['capital_provider', 'Lender or capital provider', 'I deploy debt or equity capital.'],
        ['reader', 'Market participant or reader', 'I am primarily here for market intelligence.']
      ]
    },
    capital_event: {
      id: 'capital_event',
      eyebrow: 'The decision',
      question: 'What capital event is in front of you?',
      options: [
        ['acquisition', 'Acquisition', 'Financing a purchase or recapitalizing at closing.'],
        ['refinance', 'Refinance or maturity', 'Replacing, extending, or restructuring existing debt.'],
        ['construction', 'Construction or renovation', 'Ground-up, conversion, or a major capital program.'],
        ['transition', 'Bridge or transition', 'Lease-up, repositioning, or pre-stabilization.'],
        ['recapitalization', 'Recapitalization', 'Solving a gap, partner, maturity, or balance-sheet issue.'],
        ['equity', 'Equity raise', 'JV, preferred, mezzanine, or Co-GP capital.'],
        ['disposition', 'Sale or hold decision', 'Testing a disposition against a capital alternative.'],
        ['exploring', 'Early evaluation', 'The structure or timing is not fixed yet.']
      ]
    },
    asset_market: {
      id: 'asset_market',
      type: 'compound',
      eyebrow: 'The asset',
      question: 'What are you working with?',
      fields: [
        {
          id: 'asset_type',
          label: 'Asset class',
          options: [
            ['', 'Select asset class'], ['multifamily', 'Multifamily'], ['mixed_use', 'Mixed-use'],
            ['office', 'Office'], ['retail', 'Retail'], ['industrial', 'Industrial / logistics'],
            ['hospitality', 'Hospitality'], ['student_housing', 'Student housing'],
            ['self_storage', 'Self storage'], ['medical', 'Medical / life science'],
            ['data_center', 'Data center'], ['land', 'Land / development site'], ['other', 'Other commercial real estate']
          ]
        },
        {
          id: 'market',
          label: 'Primary market',
          options: [
            ['', 'Select market'], ['nyc', 'New York City'], ['northeast', 'Northeast U.S.'],
            ['southeast', 'Southeast U.S.'], ['midwest', 'Midwest U.S.'],
            ['southwest', 'Southwest U.S.'], ['west', 'Western U.S.'],
            ['national', 'Multi-market / national'], ['other_us', 'Other U.S. market']
          ]
        }
      ]
    },
    capital_size: {
      id: 'capital_size',
      eyebrow: 'The requirement',
      question: 'What is the approximate capital need?',
      options: [
        ['under_5m', 'Under $5 million', 'A smaller-balance requirement.'],
        ['5m_20m', '$5–20 million', 'Lower-middle-market capital.'],
        ['20m_50m', '$20–50 million', 'Institutional or private-market execution.'],
        ['50m_100m', '$50–100 million', 'Large-balance capital.'],
        ['100m_250m', '$100–250 million', 'Major institutional execution.'],
        ['250m_plus', '$250 million or more', 'Large-scale or multi-asset capital.'],
        ['not_sure', 'Not yet determined', 'The requirement is still being structured.']
      ]
    },
    timeline: {
      id: 'timeline',
      eyebrow: 'The decision window',
      question: 'When must the capital decision be made?',
      options: [
        ['under_30', 'Within 30 days', 'An immediate execution window.'],
        ['30_90', '30–90 days', 'A near-term process.'],
        ['3_6', 'Three–six months', 'Planning now for a defined event.'],
        ['6_12', 'Six–twelve months', 'An early preparation window.'],
        ['exploratory', 'Still exploratory', 'No fixed deadline yet.']
      ]
    },
    constraint: {
      id: 'constraint',
      eyebrow: 'The pressure point',
      question: 'What is most likely to constrain execution?',
      options: [
        ['proceeds', 'Loan proceeds or leverage', 'The requested capital may exceed conventional proceeds.'],
        ['pricing', 'Pricing or debt service', 'The economics are sensitive to cost of capital.'],
        ['maturity', 'Maturity or closing timing', 'The available window may be shorter than the process.'],
        ['operating', 'Occupancy, NOI, or lease-up', 'The operating evidence is still developing.'],
        ['equity_gap', 'Equity or capital-stack gap', 'The senior loan does not solve the full requirement.'],
        ['recourse', 'Recourse or guarantees', 'Risk allocation matters as much as proceeds.'],
        ['control', 'Control, governance, or dilution', 'Partner economics or rights are central.'],
        ['certainty', 'Execution certainty', 'The priority is a reliable close.'],
        ['uncertain', 'Not sure yet', 'The principal constraint has not been isolated.']
      ]
    },
    referral_relationship: {
      id: 'referral_relationship',
      eyebrow: 'The relationship',
      question: 'How are you connected to the situation?',
      options: [
        ['broker', 'Broker or investment-sales advisor', 'I am advising on a transaction or asset.'],
        ['attorney', 'Attorney', 'I advise the sponsor or ownership.'],
        ['accountant', 'Accountant or financial advisor', 'I support the sponsor’s financial decisions.'],
        ['lender', 'Lender or capital source', 'The situation may need another part of the stack.'],
        ['consultant', 'Consultant or other advisor', 'I have a trusted relationship with the decision-maker.']
      ]
    },
    provider_type: {
      id: 'provider_type',
      eyebrow: 'Capital type',
      question: 'What kind of capital do you deploy?',
      options: [
        ['bank', 'Bank or credit union', 'Balance-sheet senior debt.'],
        ['debt_fund', 'Debt fund or private credit', 'Bridge, construction, or structured debt.'],
        ['life_company', 'Life company', 'Long-term fixed-rate capital.'],
        ['agency_cmbs', 'Agency or CMBS', 'Programmatic or securitized debt.'],
        ['equity_fund', 'Equity investor', 'JV, preferred, mezzanine, or Co-GP capital.'],
        ['family_office', 'Family office or private investor', 'Flexible debt or equity capital.']
      ]
    },
    provider_strategy: {
      id: 'provider_strategy',
      eyebrow: 'Strategy',
      question: 'Which execution is most relevant right now?',
      options: [
        ['permanent', 'Permanent debt'], ['bridge', 'Bridge or transitional debt'],
        ['construction', 'Construction financing'], ['structured', 'Structured or subordinate debt'],
        ['preferred', 'Preferred equity or mezzanine'], ['joint_venture', 'JV or Co-GP equity']
      ]
    },
    provider_check_size: {
      id: 'provider_check_size',
      eyebrow: 'Deployment range',
      question: 'What is your most useful check-size range?',
      options: QUESTION_BANK_PLACEHOLDER()
    },
    provider_geography: {
      id: 'provider_geography',
      eyebrow: 'Coverage',
      question: 'Where are you actively deploying?',
      options: [
        ['nyc', 'New York City'], ['northeast', 'Northeast U.S.'], ['east_coast', 'East Coast'],
        ['sunbelt', 'Sun Belt'], ['national', 'Nationwide'], ['select_markets', 'Select markets']
      ]
    },
    provider_interest: {
      id: 'provider_interest',
      eyebrow: 'Connection',
      question: 'What would make an introduction useful?',
      options: [
        ['active_mandates', 'Relevant active mandates'], ['market_dialogue', 'Market dialogue'],
        ['both', 'Both'], ['future', 'Keep my profile on file']
      ]
    },
    reader_identity: {
      id: 'reader_identity',
      eyebrow: 'Your lens',
      question: 'What is your primary role in the market?',
      options: [
        ['investor', 'Investor or allocator'], ['broker', 'Broker or advisor'],
        ['professional', 'Attorney, accountant, or consultant'], ['operator', 'Operator or asset manager'],
        ['media_academic', 'Media, academic, or research'], ['other', 'Other market participant']
      ]
    },
    reader_topic: {
      id: 'reader_topic',
      eyebrow: 'Research focus',
      question: 'Which decisions are most useful to follow?',
      options: [
        ['debt', 'Debt and refinancing'], ['development', 'Development and construction'],
        ['equity', 'Equity and recapitalization'], ['transactions', 'Transactions and basis'],
        ['operations', 'Leasing and operating performance'], ['policy', 'Policy and regulation']
      ]
    },
    reader_asset: {
      id: 'reader_asset',
      eyebrow: 'Asset focus',
      question: 'Which part of the market matters most?',
      options: [
        ['multifamily', 'Multifamily'], ['office', 'Office'], ['retail', 'Retail'],
        ['industrial', 'Industrial'], ['hospitality', 'Hospitality'],
        ['development', 'Development sites'], ['broad', 'Broad CRE capital markets']
      ]
    }
  };

  function QUESTION_BANK_PLACEHOLDER() {
    return [
      ['under_10m', 'Under $10 million'], ['10m_25m', '$10–25 million'],
      ['25m_50m', '$25–50 million'], ['50m_100m', '$50–100 million'],
      ['100m_250m', '$100–250 million'], ['250m_plus', '$250 million or more']
    ];
  }

  var DEAL_FLOW = ['role', 'capital_event', 'asset_market', 'capital_size', 'timeline', 'constraint', 'stage'];
  var REFERRAL_FLOW = ['role', 'referral_relationship', 'capital_event', 'asset_market', 'capital_size', 'timeline'];
  var PROVIDER_FLOW = ['role', 'provider_type', 'provider_strategy', 'provider_check_size', 'provider_geography', 'provider_interest'];
  var READER_FLOW = ['role', 'reader_identity', 'reader_topic', 'reader_asset'];

  function normalize(value) {
    return String(value || '').toLowerCase().replace(/[^a-z0-9$]+/g, ' ').trim();
  }

  function keywordScore(text, terms) {
    return terms.reduce(function (score, entry) {
      return score + (text.indexOf(entry[0]) !== -1 ? entry[1] : 0);
    }, 0);
  }

  function classifyTrack(context) {
    var text = normalize([
      context && context.title,
      context && context.category,
      (context && context.tags || []).join(' ')
    ].join(' '));
    if (/(^| )(construction|ground up|major renovation|development financing|entitlement)( |$)/.test(text)) return 'construction';
    if (/(^| )(recapital|distress|foreclosure|default|special servicing|workout|receivership)( |$)/.test(text)) return 'recapitalization';
    if (/(^| )(acquisition|acquires|bought|buys|purchase|sale|sells|sold|trades)( |$)/.test(text)) return 'transaction';
    if (/(^| )(lease|leasing|tenant|occupancy|noi|absorption|rollover)( |$)/.test(text)) return 'operations';
    var scores = {
      construction: keywordScore(text, [
        ['construction', 10], ['ground up', 8], ['development', 6], ['developer', 3],
        ['entitlement', 7], ['conversion', 5], ['renovation', 5], ['condominium', 4], ['land', 3]
      ]),
      recapitalization: keywordScore(text, [
        ['recapital', 10], ['distress', 9], ['foreclosure', 9], ['default', 8],
        ['special servicing', 9], ['workout', 8], ['maturity', 6], ['preferred equity', 8],
        ['mezzanine', 7], ['capital stack', 6], ['rescue', 7], ['receivership', 7]
      ]),
      refinance: keywordScore(text, [
        ['refinanc', 10], ['loan', 6], ['lender', 5], ['mortgage', 5], ['debt', 5],
        ['cmbs', 7], ['credit', 4], ['financing', 5], ['bond', 4], ['rate', 3]
      ]),
      transaction: keywordScore(text, [
        ['acquisition', 9], ['acquires', 8], ['bought', 8], ['buys', 8], ['purchase', 8],
        ['sale', 7], ['sells', 7], ['sold', 7], ['trades', 6], ['basis', 5], ['price', 3]
      ]),
      operations: keywordScore(text, [
        ['lease', 8], ['leasing', 8], ['tenant', 7], ['occupancy', 7], ['noi', 7],
        ['rent', 5], ['hotel performance', 7], ['absorption', 5], ['rollover', 7]
      ]),
      general: 1
    };
    var order = ['construction', 'recapitalization', 'refinance', 'transaction', 'operations', 'general'];
    return order.reduce(function (best, key) {
      return scores[key] > scores[best] ? key : best;
    }, 'general');
  }

  function flowForRole(role) {
    if (role === 'referral') return REFERRAL_FLOW.slice();
    if (role === 'capital_provider') return PROVIDER_FLOW.slice();
    if (role === 'reader') return READER_FLOW.slice();
    return DEAL_FLOW.slice();
  }

  function stageQuestion(capitalEvent) {
    var map = {
      acquisition: {
        question: 'Where does the acquisition stand?',
        options: [['evaluating', 'Evaluating opportunities'], ['loi', 'LOI submitted or signed'], ['contract', 'Under contract'], ['closing', 'Closing requirements are fixed']]
      },
      refinance: {
        question: 'How defined is the refinancing event?',
        options: [['early', 'Early review'], ['maturity_known', 'Maturity and request are known'], ['lender_dialogue', 'Lender dialogue has started'], ['active_process', 'An active process or extension decision']]
      },
      construction: {
        question: 'How far has the project advanced?',
        options: [['site_control', 'Site control / concept'], ['entitled', 'Entitled or approvals substantially complete'], ['equity_identified', 'Equity and budget substantially defined'], ['ready_to_close', 'Ready to finance or break ground']]
      },
      transition: {
        question: 'How visible is the stabilization path?',
        options: [['plan_forming', 'Business plan is forming'], ['milestones_defined', 'Milestones and budget are defined'], ['execution_underway', 'Execution is underway'], ['near_stabilized', 'Near stabilization or takeout']]
      },
      recapitalization: {
        question: 'How immediate is the capital-stack decision?',
        options: [['reviewing', 'Reviewing alternatives'], ['negotiating', 'Partner or lender discussions underway'], ['deadline', 'A defined maturity or decision deadline'], ['urgent', 'Immediate restructuring need']]
      },
      equity: {
        question: 'How defined is the equity requirement?',
        options: [['concept', 'Early structure'], ['economics', 'Economics and control priorities defined'], ['materials', 'Materials and sponsor equity defined'], ['active_raise', 'Active raise or closing process']]
      },
      disposition: {
        question: 'How far has the sale-or-hold decision advanced?',
        options: [['evaluating', 'Evaluating alternatives'], ['valuation', 'Valuation or broker opinion in hand'], ['market_ready', 'Ready to test the market'], ['active_process', 'Active sale or recap process']]
      },
      exploring: {
        question: 'What would make the next step more concrete?',
        options: [['market_context', 'Better market context'], ['capital_range', 'A realistic capital range'], ['structure', 'Clarity on structure'], ['timing', 'A defined decision date']]
      }
    };
    var selected = map[capitalEvent] || map.exploring;
    return {
      id: 'stage',
      eyebrow: 'The current stage',
      question: selected.question,
      options: selected.options
    };
  }

  function questionFor(id, answers) {
    return id === 'stage' ? stageQuestion(answers.capital_event) : QUESTION_BANK[id];
  }

  function scoreSubmission(answers) {
    answers = answers || {};
    var role = answers.role;
    if (role === 'capital_provider') return { total: 0, fit: 0, intent: 0, executionNeed: 0, readiness: 0, route: 'capital_provider', outcome: 'provider_profile' };
    if (role === 'reader') return { total: 0, fit: 0, intent: 0, executionNeed: 0, readiness: 0, route: 'reader', outcome: 'reader_profile' };
    if (role === 'referral') return { total: 45, fit: 20, intent: 15, executionNeed: 10, readiness: 0, route: 'referral', outcome: 'referral_profile' };

    var fit = role === 'sponsor_owner' || role === 'developer' ? 20 : 0;
    fit += ['5m_20m', '20m_50m', '50m_100m', '100m_250m', '250m_plus'].indexOf(answers.capital_size) !== -1 ? 15 : (answers.capital_size === 'under_5m' ? 4 : 7);
    fit += answers.asset_type && answers.asset_type !== 'other' ? 3 : 1;
    fit += answers.market ? 2 : 0;

    var intentMap = { under_30: 30, '30_90': 24, '3_6': 17, '6_12': 9, exploratory: 3 };
    var intent = intentMap[answers.timeline] || 0;
    var executionNeed = answers.capital_event && answers.capital_event !== 'exploring' ? 10 : 4;
    executionNeed += answers.constraint && answers.constraint !== 'uncertain' ? 10 : 3;

    var readinessValues = {
      contract: 10, closing: 10, active_process: 10, ready_to_close: 10, urgent: 10, active_raise: 10,
      loi: 8, lender_dialogue: 8, execution_underway: 8, deadline: 9, materials: 8, market_ready: 8,
      entitled: 6, equity_identified: 8, maturity_known: 6, milestones_defined: 6, economics: 6,
      evaluating: 3, early: 3, site_control: 3, plan_forming: 3, reviewing: 4, concept: 3,
      valuation: 5, near_stabilized: 9, market_context: 2, capital_range: 3, structure: 3, timing: 2
    };
    var readiness = readinessValues[answers.stage] || 0;
    var total = Math.min(100, fit + intent + executionNeed + readiness);
    var route = total >= 70 ? 'priority_mandate' : (total >= 45 ? 'qualified_nurture' : 'future_nurture');
    var outcome = 'structure_before_market';
    if (answers.timeline === '6_12' || answers.timeline === 'exploratory' || answers.capital_event === 'exploring') {
      outcome = 'planning_window';
    } else if (
      ['recapitalization', 'equity'].indexOf(answers.capital_event) !== -1 ||
      ['maturity', 'equity_gap', 'control'].indexOf(answers.constraint) !== -1
    ) {
      outcome = 'capital_stack_pressure';
    } else if (total >= 70) {
      outcome = 'ready_to_run';
    }
    return { total: total, fit: fit, intent: intent, executionNeed: executionNeed, readiness: readiness, route: route, outcome: outcome };
  }

  function resultBrief(track, answers) {
    var scoring = scoreSubmission(answers);
    var trackData = TRACKS[track] || TRACKS.general;
    var outcome = OUTCOMES[scoring.outcome] || OUTCOMES.structure_before_market;
    return {
      track: track,
      trackLabel: trackData.label,
      outcome: scoring.outcome,
      title: outcome.title,
      description: outcome.description,
      pressure: trackData.pressure,
      prepare: trackData.prepare,
      compare: trackData.compare,
      next: outcome.next,
      scoring: scoring
    };
  }

  function articleContext(doc, locationObject) {
    var titleEl = doc.querySelector('.article-title, .post-title, article h1, h1');
    var categoryEl = doc.querySelector('.article-category, .post-category');
    var tags = Array.prototype.map.call(doc.querySelectorAll('.article-tags .tag'), function (tag) {
      return tag.textContent.trim();
    }).filter(Boolean);
    var path = locationObject.pathname || '';
    var params = new URLSearchParams(locationObject.search || '');
    var context = {
      slug: ((path.match(/\/insights\/([^/]+)\.html$/i) || [])[1] || '').slice(0, 180),
      path: path.slice(0, 240),
      title: titleEl ? titleEl.textContent.trim().slice(0, 300) : '',
      category: categoryEl ? categoryEl.textContent.trim().slice(0, 120) : '',
      tags: tags.slice(0, 12),
      referrer: (doc.referrer || '').slice(0, 500),
      utm_source: (params.get('utm_source') || '').slice(0, 120),
      utm_medium: (params.get('utm_medium') || '').slice(0, 120),
      utm_campaign: (params.get('utm_campaign') || '').slice(0, 160),
      utm_content: (params.get('utm_content') || '').slice(0, 160),
      utm_term: (params.get('utm_term') || '').slice(0, 160)
    };
    context.track = classifyTrack(context);
    return context;
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function randomId() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 'ltg-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 12);
  }

  function mount(doc, win) {
    if (!doc || doc.getElementById('ltg-capital-diagnostic')) return null;
    if (!/\/insights\/[^/]+\.html$/i.test(win.location.pathname)) return null;
    var context = articleContext(doc, win.location);
    var track = TRACKS[context.track] || TRACKS.general;
    var rootEl = doc.createElement('section');
    rootEl.id = 'ltg-capital-diagnostic';
    rootEl.className = 'ltg-capital-diagnostic';
    rootEl.setAttribute('aria-labelledby', 'ltg-diagnostic-title');
    rootEl.dataset.track = context.track;

    var oldCta = doc.querySelector('.article-cta-block, .post-cta');
    var sources = doc.querySelector('.sources-block');
    var related = doc.querySelector('.related-research');
    var article = doc.querySelector('.article-wrap article, main article, article');
    if (oldCta) oldCta.replaceWith(rootEl);
    else if (related && related.parentNode) related.parentNode.insertBefore(rootEl, related);
    else if (sources && sources.parentNode) sources.parentNode.insertBefore(rootEl, sources);
    else if (article) article.appendChild(rootEl);
    else return null;

    var state = {
      context: context,
      answers: {},
      flow: DEAL_FLOW.slice(),
      index: -1,
      submissionId: randomId()
    };

    function trackEvent(name, extra) {
      if (!win.ltgTrack) return;
      win.ltgTrack(name, Object.assign({
        diagnostic_version: VERSION,
        article_slug: context.slug,
        diagnostic_track: context.track
      }, extra || {}));
    }

    function shell(content, mode) {
      rootEl.className = 'ltg-capital-diagnostic ltg-diagnostic--' + mode;
      rootEl.innerHTML =
        '<div class="ltg-diagnostic__frame">' +
          '<div class="ltg-diagnostic__signal" aria-hidden="true"><span></span><span></span><span></span></div>' +
          '<div class="ltg-diagnostic__topline">' +
            '<span>Light Tower Group / Capital Intelligence</span>' +
            '<span>' + escapeHtml(track.label) + '</span>' +
          '</div>' +
          '<div class="ltg-diagnostic__content">' + content + '</div>' +
        '</div>';
    }

    function renderIntro() {
      shell(
        '<div class="ltg-diagnostic__intro">' +
          '<div>' +
            '<p class="ltg-diagnostic__eyebrow">' + escapeHtml(track.eyebrow) + '</p>' +
            '<h2 id="ltg-diagnostic-title">' + escapeHtml(track.headline) + '</h2>' +
            '<p class="ltg-diagnostic__lead">' + escapeHtml(track.intro) + '</p>' +
          '</div>' +
          '<div class="ltg-diagnostic__start-panel">' +
            '<p class="ltg-diagnostic__time">90 seconds <span aria-hidden="true">/</span> no documents required</p>' +
            '<button type="button" class="ltg-diagnostic__primary" data-diagnostic-start>Run the capital review <span aria-hidden="true">→</span></button>' +
            '<p class="ltg-diagnostic__trust">Private, non-binding, and designed for commercial real estate capital decisions of approximately $5 million and above.</p>' +
          '</div>' +
        '</div>', 'intro'
      );
      rootEl.querySelector('[data-diagnostic-start]').addEventListener('click', function () {
        state.index = 0;
        trackEvent('diagnostic_start');
        renderQuestion();
      });
    }

    function progressMarkup(total) {
      var current = state.index + 1;
      var pct = Math.round((current / total) * 100);
      return '<div class="ltg-diagnostic__progress-wrap">' +
        '<div class="ltg-diagnostic__progress-meta"><span>Capital review</span><span>Step ' + current + ' of ' + total + '</span></div>' +
        '<div class="ltg-diagnostic__progress" role="progressbar" aria-valuemin="1" aria-valuemax="' + total + '" aria-valuenow="' + current + '" aria-valuetext="Step ' + current + ' of ' + total + '">' +
          '<span style="width:' + pct + '%"></span>' +
        '</div>' +
      '</div>';
    }

    function renderQuestion() {
      var id = state.flow[state.index];
      var question = questionFor(id, state.answers);
      if (!question) return renderResult();
      var controls = '';
      if (question.type === 'compound') {
        controls = '<div class="ltg-diagnostic__compound">' + question.fields.map(function (field) {
          return '<label><span>' + escapeHtml(field.label) + '</span><select data-answer-field="' + escapeHtml(field.id) + '">' +
            field.options.map(function (option) {
              var selected = state.answers[field.id] === option[0] ? ' selected' : '';
              return '<option value="' + escapeHtml(option[0]) + '"' + selected + '>' + escapeHtml(option[1]) + '</option>';
            }).join('') +
          '</select></label>';
        }).join('') + '</div>' +
          '<button type="button" class="ltg-diagnostic__primary ltg-diagnostic__continue" data-compound-next>Continue <span aria-hidden="true">→</span></button>' +
          '<p class="ltg-diagnostic__error" role="alert" data-question-error></p>';
      } else {
        controls = '<div class="ltg-diagnostic__choices">' + question.options.map(function (option) {
          var chosen = state.answers[question.id] === option[0];
          return '<button type="button" class="ltg-diagnostic__choice' + (chosen ? ' is-selected' : '') + '" data-choice="' + escapeHtml(option[0]) + '" aria-pressed="' + (chosen ? 'true' : 'false') + '">' +
            '<span class="ltg-diagnostic__choice-title">' + escapeHtml(option[1]) + '</span>' +
            (option[2] ? '<span class="ltg-diagnostic__choice-sub">' + escapeHtml(option[2]) + '</span>' : '') +
            '<span class="ltg-diagnostic__choice-mark" aria-hidden="true">↗</span>' +
          '</button>';
        }).join('') + '</div>';
      }
      shell(
        progressMarkup(state.flow.length) +
        '<div class="ltg-diagnostic__question-head">' +
          '<p class="ltg-diagnostic__eyebrow">' + escapeHtml(question.eyebrow) + '</p>' +
          '<h2 id="ltg-diagnostic-title" tabindex="-1">' + escapeHtml(question.question) + '</h2>' +
        '</div>' +
        controls +
        '<div class="ltg-diagnostic__nav"><button type="button" class="ltg-diagnostic__back" data-diagnostic-back>← Back</button><span>Responses remain private.</span></div>',
        'question'
      );
      var heading = rootEl.querySelector('#ltg-diagnostic-title');
      if (heading) heading.focus({ preventScroll: true });
      trackEvent('diagnostic_step', { step_id: question.id, step_number: state.index + 1 });
      rootEl.querySelector('[data-diagnostic-back]').addEventListener('click', function () {
        if (state.index <= 0) {
          state.index = -1;
          renderIntro();
        } else {
          state.index -= 1;
          renderQuestion();
        }
      });
      rootEl.querySelectorAll('[data-choice]').forEach(function (button) {
        button.addEventListener('click', function () {
          state.answers[question.id] = button.dataset.choice;
          if (question.id === 'role') state.flow = flowForRole(state.answers.role);
          state.index += 1;
          if (state.index >= state.flow.length) renderResult();
          else renderQuestion();
        });
      });
      var compoundNext = rootEl.querySelector('[data-compound-next]');
      if (compoundNext) {
        compoundNext.addEventListener('click', function () {
          var valid = true;
          question.fields.forEach(function (field) {
            var select = rootEl.querySelector('[data-answer-field="' + field.id + '"]');
            state.answers[field.id] = select.value;
            if (!select.value) valid = false;
          });
          if (!valid) {
            rootEl.querySelector('[data-question-error]').textContent = 'Select both the asset class and primary market to continue.';
            return;
          }
          state.index += 1;
          if (state.index >= state.flow.length) renderResult();
          else renderQuestion();
        });
      }
    }

    function renderResult() {
      var brief = resultBrief(context.track, state.answers);
      var isDeal = ['sponsor_owner', 'developer'].indexOf(state.answers.role) !== -1;
      var reviewLine = isDeal || state.answers.role === 'referral'
        ? '<label class="ltg-diagnostic__check ltg-diagnostic__check--priority"><input type="checkbox" name="request_review"><span><strong>Request a confidential review</strong>Ask Benjamin Rohr to review this profile and contact me about the scenario.</span></label>'
        : '';
      shell(
        '<div class="ltg-diagnostic__result-grid">' +
          '<div class="ltg-diagnostic__result-main">' +
            '<p class="ltg-diagnostic__eyebrow">Your capital-readiness brief</p>' +
            '<h2 id="ltg-diagnostic-title" tabindex="-1">' + escapeHtml(brief.title) + '</h2>' +
            '<p class="ltg-diagnostic__result-description">' + escapeHtml(brief.description) + '</p>' +
            '<div class="ltg-diagnostic__brief-list">' +
              '<div><span>Likely pressure point</span><p>' + escapeHtml(brief.pressure) + '</p></div>' +
              '<div><span>Prepare next</span><p>' + escapeHtml(brief.prepare) + '</p></div>' +
              '<div><span>Structures to compare—not a recommendation</span><p>' + escapeHtml(brief.compare) + '</p></div>' +
            '</div>' +
            '<p class="ltg-diagnostic__next"><strong>Suggested next move:</strong> ' + escapeHtml(brief.next) + '</p>' +
          '</div>' +
          '<form class="ltg-diagnostic__contact" data-diagnostic-form novalidate>' +
            '<p class="ltg-diagnostic__form-kicker">Send the private brief</p>' +
            '<h3>Keep the analysis and choose your follow-up.</h3>' +
            '<div class="ltg-diagnostic__fields">' +
              '<label><span>Full name</span><input type="text" name="name" autocomplete="name" maxlength="160" required></label>' +
              '<label><span>Work email</span><input type="email" name="email" autocomplete="email" maxlength="254" required></label>' +
              '<label><span>Company <em>optional</em></span><input type="text" name="company" autocomplete="organization" maxlength="200"></label>' +
              '<label><span>Mobile number <em>optional</em></span><input type="tel" name="phone" autocomplete="tel" maxlength="40"></label>' +
              '<label class="ltg-diagnostic__honeypot" aria-hidden="true">Website<input type="text" name="website" tabindex="-1" autocomplete="off"></label>' +
            '</div>' +
            reviewLine +
            '<label class="ltg-diagnostic__check"><input type="checkbox" name="email_consent"><span><strong>Light Tower Insights by email</strong>Send me future research and capital-markets updates. I can unsubscribe at any time.</span></label>' +
            '<label class="ltg-diagnostic__check"><input type="checkbox" name="sms_consent"><span><strong>Relevant text updates</strong>I agree to occasional Light Tower Group texts about this capital profile and related CRE market developments. Message frequency varies. Message and data rates may apply. Reply STOP to opt out or HELP for help. Consent is not a condition of service.</span></label>' +
            '<p class="ltg-diagnostic__legal">The requested brief is a one-time operational email. Marketing permissions above are separate. See the <a href="/privacy.html">Privacy Notice</a> and <a href="/sms-terms.html">Messaging Terms</a>.</p>' +
            '<p class="ltg-diagnostic__form-error" role="alert" data-form-error></p>' +
            '<button type="submit" class="ltg-diagnostic__primary" data-submit>Send my private brief <span aria-hidden="true">→</span></button>' +
            '<button type="button" class="ltg-diagnostic__back ltg-diagnostic__result-back" data-result-back>← Review my answers</button>' +
          '</form>' +
        '</div>', 'result'
      );
      trackEvent('diagnostic_complete', { diagnostic_outcome: brief.outcome, lead_route: brief.scoring.route });
      var resultHeading = rootEl.querySelector('#ltg-diagnostic-title');
      if (resultHeading) resultHeading.focus({ preventScroll: true });
      rootEl.querySelector('[data-result-back]').addEventListener('click', function () {
        state.index = Math.max(0, state.flow.length - 1);
        renderQuestion();
      });
      rootEl.querySelector('[data-diagnostic-form]').addEventListener('submit', function (event) {
        event.preventDefault();
        submitForm(event.currentTarget, brief);
      });
    }

    function submitForm(form, brief) {
      var errorEl = form.querySelector('[data-form-error]');
      var submit = form.querySelector('[data-submit]');
      var data = new FormData(form);
      var email = String(data.get('email') || '').trim();
      var name = String(data.get('name') || '').trim();
      var phone = String(data.get('phone') || '').trim();
      var smsConsent = data.get('sms_consent') === 'on';
      errorEl.textContent = '';
      if (!name || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        errorEl.textContent = 'Enter your name and a valid work email.';
        return;
      }
      if (smsConsent && phone.replace(/\D/g, '').length < 7) {
        errorEl.textContent = 'Add a valid mobile number to request text updates.';
        return;
      }
      submit.disabled = true;
      submit.textContent = 'Sending your brief…';
      var payload = {
        submission_id: state.submissionId,
        diagnostic_version: VERSION,
        consent_version: CONSENT_VERSION,
        sms_disclosure_version: SMS_DISCLOSURE_VERSION,
        name: name,
        email: email,
        company: String(data.get('company') || '').trim(),
        phone: phone,
        website: String(data.get('website') || ''),
        request_review: data.get('request_review') === 'on',
        email_consent: data.get('email_consent') === 'on',
        sms_consent: smsConsent,
        answers: state.answers,
        context: state.context
      };
      var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
      var timer = controller ? setTimeout(function () { controller.abort(); }, 15000) : null;
      fetch('/.netlify/functions/capital-diagnostic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller ? controller.signal : undefined
      }).then(function (response) {
        return response.json().catch(function () { return {}; }).then(function (body) {
          if (!response.ok) throw new Error(body.error || 'The brief could not be delivered.');
          return body;
        });
      }).then(function (response) {
        if (timer) clearTimeout(timer);
        trackEvent('diagnostic_contact_submit', {
          diagnostic_outcome: brief.outcome,
          lead_route: brief.scoring.route,
          review_requested: payload.request_review,
          email_permission: payload.email_consent,
          sms_permission: payload.sms_consent
        });
        renderSuccess(response, payload, brief);
      }).catch(function (error) {
        if (timer) clearTimeout(timer);
        submit.disabled = false;
        submit.innerHTML = 'Send my private brief <span aria-hidden="true">→</span>';
        errorEl.textContent = error.name === 'AbortError'
          ? 'The request took too long. Please try once more or email ben@lighttowergroup.co.'
          : error.message;
      });
    }

    function renderSuccess(response, payload, brief) {
      var reviewCopy = payload.request_review
        ? 'Benjamin Rohr will review the profile and respond personally, typically within one business day.'
        : 'Your brief is on its way. No advisory follow-up was requested.';
      shell(
        '<div class="ltg-diagnostic__success">' +
          '<p class="ltg-diagnostic__eyebrow">Capital brief sent</p>' +
          '<h2 id="ltg-diagnostic-title" tabindex="-1">Your next move is clearer.</h2>' +
          '<p>' + escapeHtml(reviewCopy) + '</p>' +
          '<div class="ltg-diagnostic__success-card">' +
            '<span>Your result</span><strong>' + escapeHtml(brief.title) + '</strong>' +
            '<p>Reference ' + escapeHtml((response && response.reference) || state.submissionId.slice(0, 12)) + '</p>' +
          '</div>' +
          '<div class="ltg-diagnostic__success-actions">' +
            '<a href="/services.html">Explore capital advisory services <span aria-hidden="true">→</span></a>' +
            '<a href="/insights.html">Return to Intelligence</a>' +
          '</div>' +
        '</div>', 'success'
      );
      var heading = rootEl.querySelector('#ltg-diagnostic-title');
      if (heading) heading.focus({ preventScroll: true });
    }

    renderIntro();
    if ('IntersectionObserver' in win) {
      var observer = new win.IntersectionObserver(function (entries) {
        if (entries.some(function (entry) { return entry.isIntersecting; })) {
          trackEvent('diagnostic_impression');
          observer.disconnect();
        }
      }, { threshold: 0.25 });
      observer.observe(rootEl);
    } else {
      trackEvent('diagnostic_impression');
    }
    return { element: rootEl, state: state, context: context };
  }

  function boot() {
    if (typeof document === 'undefined' || typeof window === 'undefined') return;
    var run = function () { mount(document, window); };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run, { once: true });
    else run();
  }

  return {
    VERSION: VERSION,
    CONSENT_VERSION: CONSENT_VERSION,
    SMS_DISCLOSURE_VERSION: SMS_DISCLOSURE_VERSION,
    TRACKS: TRACKS,
    OUTCOMES: OUTCOMES,
    QUESTION_BANK: QUESTION_BANK,
    classifyTrack: classifyTrack,
    flowForRole: flowForRole,
    questionFor: questionFor,
    scoreSubmission: scoreSubmission,
    resultBrief: resultBrief,
    articleContext: articleContext,
    mount: mount,
    boot: boot
  };
});
