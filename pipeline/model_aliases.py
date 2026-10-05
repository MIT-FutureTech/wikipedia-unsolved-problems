"""Every AI system string the research records name, mapped to a canonical model.

The deep dive records each system exactly as its source named it (DEEP_DIVE.md §6.5), which is
right for evidence and useless for counting: "GPT 5.6 Sol", "gpt-5.6-sol" and "Chatgpt 5.6 Solar"
are one model. This file is the only place that judgement lives.

  MODELS   canonical name -> lab, family, kind, release date
           kind: shipped | tier | internal | harness | method | unnamed
           release is None until the release-date pass runs; None is a gap, never a guess.
  ALIASES  raw string from a record -> canonical name, or None to drop it from the model counts

How the mapping was arrived at, in order of preference:

  1. **From the record itself.** Most labs were read off the deep-dive summaries, which name the
     owner in passing: "Harmonic's Aristotle theorem-proving system", "Axiom Math's AxiomProver",
     "a Peking-University-led team introduced PackingStar", "Yuksekgonul et al.'s TTT-Discover",
     "Ye et al.'s SimpleTES". No research needed; the evidence is already in the dataset.
  2. **From the web, where the record named a system but not its owner.** Two: Refine, the
     verification tool that found gaps in the Hopf conjecture preprint, is Refine Technologies
     (refine.ink, @RefineDotInk); the Danus system is a multi-agent proof orchestrator from a
     Peking-University-led group (Liu et al., arXiv:2607.06447, first affiliation School of
     Mathematical Sciences, Peking University).
  3. **From the string alone**, where neither of the above said anything. These are marked REVIEW
     and are guesses — mostly whether an unqualified name means a base model or one of its tiers.

`lab` stays None only where no source found names an owner: currently just `unnamed model`, the
placeholder for records whose sources credit "an AI" and nothing more.

A record coded `ai_role: none` contributes nothing here, however many systems it names. Its
systems stay in the record as evidence and are excluded from the model counts by
merge_research.systems_of — see the Petersen-minor bullet, where the authors credit Copilot with
writing their verification code.
"""

MODELS = {
    # --- OpenAI
    'GPT-5':              dict(lab='OpenAI', family='GPT-5',     kind='shipped',  release=None),
    'GPT-5.5 Pro':        dict(lab='OpenAI', family='GPT-5.5',   kind='tier',     release=None),
    'GPT-5.6 Sol':        dict(lab='OpenAI', family='GPT-5.6',   kind='shipped',  release=None),
    'GPT-5.6 Sol Pro':    dict(lab='OpenAI', family='GPT-5.6',   kind='tier',     release=None),
    'GPT-5.6 Sol Ultra':  dict(lab='OpenAI', family='GPT-5.6',   kind='tier',     release=None),
    'GPT-6 Astra':        dict(lab='OpenAI', family='GPT-6',     kind='shipped',  release=None),
    'ChatGPT':            dict(lab='OpenAI', family='ChatGPT',   kind='harness',  release=None),
    'Codex':              dict(lab='OpenAI', family='Codex',     kind='harness',  release=None),
    'gpt-oss-120b':       dict(lab='OpenAI', family='gpt-oss',   kind='shipped',  release=None),
    'gpt-oss-20b':        dict(lab='OpenAI', family='gpt-oss',   kind='shipped',  release=None),
    'OpenAI internal model': dict(lab='OpenAI', family=None,     kind='internal', release=None),

    # --- Anthropic
    'Claude':             dict(lab='Anthropic', family='Claude', kind='unnamed',  release=None),
    'Claude Code':        dict(lab='Anthropic', family='Claude', kind='harness',  release=None),
    'Claude Fable 5':     dict(lab='Anthropic', family='Fable 5', kind='shipped', release=None),
    'Claude Fable 5.1':   dict(lab='Anthropic', family='Fable 5', kind='shipped', release=None),
    'Claude Opus 4.6':    dict(lab='Anthropic', family='Opus 4',  kind='shipped', release=None),
    'Claude Opus 4.7':    dict(lab='Anthropic', family='Opus 4',  kind='shipped', release=None),
    'Claude Opus 4.8':    dict(lab='Anthropic', family='Opus 4',  kind='shipped', release=None),
    'Claude Opus 5':      dict(lab='Anthropic', family='Opus 5',  kind='shipped', release=None),
    'Claude Sonnet 3.7':  dict(lab='Anthropic', family='Sonnet 3', kind='shipped', release=None),
    'Anthropic internal model': dict(lab='Anthropic', family=None, kind='internal', release=None),

    # --- Google
    'Gemini':             dict(lab='Google DeepMind', family='Gemini', kind='unnamed', release=None),
    'Gemini 2.0 Flash':   dict(lab='Google DeepMind', family='Gemini 2', kind='shipped', release=None),
    'Gemini 2.0 Pro':     dict(lab='Google DeepMind', family='Gemini 2', kind='shipped', release=None),
    'Gemini 2.5 Pro':     dict(lab='Google DeepMind', family='Gemini 2', kind='shipped', release=None),
    'Gemini 3 Pro':       dict(lab='Google DeepMind', family='Gemini 3', kind='shipped', release=None),
    'Gemini 3.1 Pro':     dict(lab='Google DeepMind', family='Gemini 3', kind='shipped', release=None),
    'Gemini Deep Think':  dict(lab='Google DeepMind', family='Gemini',   kind='tier',    release=None),
    'AlphaEvolve':        dict(lab='Google DeepMind', family=None, kind='harness', release=None),
    'AlphaProof Nexus':   dict(lab='Google DeepMind', family=None, kind='harness', release=None),

    # --- xAI, Microsoft
    'Grok 4.6':           dict(lab='xAI',       family='Grok 4', kind='shipped', release=None),
    'Grok 4.20':          dict(lab='xAI',       family='Grok 4', kind='shipped', release=None),
    'Grok':               dict(lab='xAI',       family='Grok',   kind='unnamed', release=None),
    'GitHub Copilot':     dict(lab='Microsoft', family=None,     kind='harness', release=None),

    # --- systems named by one or two records; labs read off the records' own summaries
    'Aristotle':          dict(lab='Harmonic', family=None, kind='harness', release=None),
    'AxiomProver':        dict(lab='Axiom Math', family=None, kind='harness', release=None),
    'PackingStar':        dict(lab='Peking University (Ma et al.)', family=None, kind='harness', release=None),
    'Refine':             dict(lab='Refine Technologies', family=None, kind='harness', release=None),
    'SimpleTES':          dict(lab='Ye et al. (academic)', family=None, kind='harness', release=None),  # built on gpt-oss-120b/20b
    'TTT-Discover':       dict(lab='Yuksekgonul et al. (academic)', family=None, kind='harness', release=None),
    'Xiaozhua':           dict(lab=None, family=None, kind='harness', release=None),  # writing assistant; never credited with mathematics
    'the Danus system':   dict(lab='Peking University (Liu et al.)', family=None, kind='harness', release=None),
    'EinsteinArena':      dict(lab='Together AI', family=None, kind='harness', release=None),
    'Caltech RL system':  dict(lab='Caltech Math-AI Lab', family=None, kind='internal', release=None),
    'unnamed model':      dict(lab=None, family=None, kind='unnamed', release=None),
}

# Product and family names that pin down no version. build.py shows them as "<name> (unknown
# version)" everywhere a reader sees them, so an unqualified "Claude" is not read as one model.
# The canonical keys stay as they are, since release_dates.json is keyed on them.
UNVERSIONED = {'Claude', 'ChatGPT', 'Codex', 'Claude Code', 'Gemini', 'Grok', 'GitHub Copilot'}

ALIASES = {
    # OpenAI — GPT-5.6 Sol and its tiers
    'GPT-5.6 Sol': 'GPT-5.6 Sol', 'GPT 5.6 Sol': 'GPT-5.6 Sol', 'gpt-5.6-sol': 'GPT-5.6 Sol',
    'GPT-5.6-sol': 'GPT-5.6 Sol', 'OpenAI GPT-5.6 Sol': 'GPT-5.6 Sol',
    'ChatGPT 5.6 Sol': 'GPT-5.6 Sol', 'Chatgpt 5.6 Solar': 'GPT-5.6 Sol',   # REVIEW spelling
    'GPT 5.6': 'GPT-5.6 Sol', 'ChatGPT 5.6': 'GPT-5.6 Sol',                 # REVIEW: tier unstated
    'GPT-5.6 Sol Pro': 'GPT-5.6 Sol Pro', 'ChatGPT 5.6 Sol Pro': 'GPT-5.6 Sol Pro',
    'GPT-5.6 Pro': 'GPT-5.6 Sol Pro',                                        # REVIEW
    'GPT-5.6 Sol (OpenAI, model gpt-5.6-sol-pro)': 'GPT-5.6 Sol Pro',
    'GPT-5.6 Sol Ultra': 'GPT-5.6 Sol Ultra',
    # OpenAI — GPT-6 Astra
    'GPT-6 Astra': 'GPT-6 Astra', 'GPT 6 Astra': 'GPT-6 Astra', 'GPT6 Astra': 'GPT-6 Astra',
    'gpt-6-astra': 'GPT-6 Astra', 'Astra': 'GPT-6 Astra',
    'GPT-6 Astra (pre-release)': 'GPT-6 Astra',                              # pre-release: see summary
    'ChatGPT 6': 'GPT-6 Astra', 'GPT 6': 'GPT-6 Astra',                      # REVIEW
    # OpenAI — older and generic
    'GPT-5.5 Pro': 'GPT-5.5 Pro', 'GPT 5.5 Pro': 'GPT-5.5 Pro', 'GPT-5': 'GPT-5',
    'ChatGPT 5.4': 'GPT-5', 'ChatGPT': 'ChatGPT', 'ChatGPT (OpenAI)': 'ChatGPT',
    'OpenAI ChatGPT': 'ChatGPT', 'ChatGPT Pro': 'ChatGPT',                   # REVIEW: Pro tier
    'Codex': 'Codex', 'OpenAI Codex': 'Codex',
    'OpenAI Codex (GPT-5.6 family)': 'Codex', 'OpenAI Codex (GPT-5.6 Sol)': 'Codex',
    'gpt-oss-120b': 'gpt-oss-120b', 'gpt-oss-20b': 'gpt-oss-20b',
    'OpenAI language-model systems': 'OpenAI internal model',                # REVIEW
    'an internal general-purpose reasoning model of OpenAI': 'OpenAI internal model',
    'an OpenAI internal model significantly more capable than GPT-6 Astra': 'OpenAI internal model',
    # Anthropic
    'Claude': 'Claude', 'Claude (Anthropic)': 'Claude',
    'Claude Code': 'Claude Code',
    'Anthropic Claude Code (Claude 5 family)': 'Claude Code',
    'Anthropic Claude Code (Opus 5.0)': 'Claude Code',                       # REVIEW: harness + model
    'Claude Fable 5': 'Claude Fable 5', 'Fable 5': 'Claude Fable 5',
    'Claude (Fable 5)': 'Claude Fable 5', 'Anthropic Claude Fable 5': 'Claude Fable 5',
    'Claude Fable 5.1': 'Claude Fable 5.1',
    'Claude Opus 4.6': 'Claude Opus 4.6', 'Claude Opus 4.6 Extended': 'Claude Opus 4.6',
    'Claude Opus 4.7': 'Claude Opus 4.7', 'Claude Opus 4.8': 'Claude Opus 4.8',
    'Claude Opus 5': 'Claude Opus 5', 'Claude Sonnet 3.7': 'Claude Sonnet 3.7',
    'an internal research version of Claude': 'Anthropic internal model',
    'unreleased Claude': 'Anthropic internal model',
    # Google
    'Gemini': 'Gemini', 'Google Gemini (Web version)': 'Gemini',
    'Gemini 2.0 Flash': 'Gemini 2.0 Flash', 'Gemini-2.0 Pro': 'Gemini 2.0 Pro',
    'gemini-2.5-pro': 'Gemini 2.5 Pro', 'gemini-3-pro': 'Gemini 3 Pro',
    'Gemini 3 Pro': 'Gemini 3 Pro', 'Gemini 3.1 Pro': 'Gemini 3.1 Pro',
    'Gemini Deep Think': 'Gemini Deep Think',
    'AlphaEvolve': 'AlphaEvolve', 'AlphaProof Nexus': 'AlphaProof Nexus',
    # xAI, Microsoft
    'Grok 4.6': 'Grok 4.6', 'Grok 4.20': 'Grok 4.20', 'GROK': 'Grok',
    'GitHub Copilot': 'GitHub Copilot', 'Copilot': 'GitHub Copilot',          # REVIEW
    # harnesses and one-off systems
    'Aristotle': 'Aristotle', 'AxiomProver': 'AxiomProver', 'PackingStar': 'PackingStar',
    'Refine': 'Refine', 'SimpleTES': 'SimpleTES', 'TTT-Discover': 'TTT-Discover',
    'Xiaozhua': 'Xiaozhua', 'the Danus system': 'the Danus system',
    'TogetherAI EinsteinArena agents': 'EinsteinArena',
    'Caltech Math-AI Lab RL system (unnamed)': 'Caltech RL system',
    # named systems with no model behind them
    'an unnamed AI model/system (not identified by name in any source found)': 'unnamed model',
    'four-agent adversarial AI review panel (unnamed models)': 'unnamed model',

    # Not models. These stay in the record's own `ai.systems` as evidence, but they are dropped
    # from the model counts: a training algorithm and two method descriptions, not systems.
    'Proximal Policy Optimization (PPO) algorithm': None,
    'piecewise linear neural networks': None,
    'physics-informed machine learning': None,
}
