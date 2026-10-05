"""Synthetic version-1 deck examples covering every component."""
import copy


def components():
    return [
        dict(type='cold', big='12', headline='A synthetic week', lede='A deterministic preview.', small='Counts are synthetic.'),
        dict(type='bignum', value=1200, lede='Measured tokens', bars=[dict(label='By agent',segments=[dict(agent='codex',label='Codex',value=1200)])], small='Token counts differ across vendors; exports are estimates.'),
        dict(type='lineup',headline='Your coding agent',acts=[dict(agent='codex',prompts=12,sessions=3,tokens_label='1,200',role='Builder',line='A useful role',surfaces='CLI')]),
        dict(type='ranking',headline='Projects',rows=[dict(name='Demo',value_label='1,200',segments=[dict(agent='codex',value=1200)],meta='Synthetic project')]),
        dict(type='quote',headline='An opener',quote='Please show your evidence',tally=[dict(label='Requests',value=12,suffix='×')]),
        dict(type='tally',headline='Small habits',tally=[dict(label='Thanks',value=12,suffix='×')]),
        dict(type='compare',headline='A comparison',rows=[dict(label='With context',pct=80,n_label='n=20'),dict(label='Without',pct=60,n_label='n=20')]),
        dict(type='timeline',headline='A day',items=[dict(time='10:00',agent='codex',text='Worked on a synthetic task')]),
        dict(type='heatmap',headline='Your activity',days=[dict(key='2026-10-05',label='Mon')],hours=[10,11],cells={'2026-10-05|10':{'codex':2}},alt='Two prompts on Monday at ten'),
        dict(type='coach',kind='win',confidence='one moment',headline='Context helped',stat=dict(type='quote',quote='Please show your evidence'),why='A clear request made the next step concrete.',**{'try':'Ask for one example.'},evidence_refs=['/coaching/summary/candidates']),
        dict(type='archetype',name='The Builder',lede='A synthetic persona',evidence=[dict(label='Prompts',value=12),dict(label='Projects',value=1),dict(label='Sessions',value=3)]),
        dict(type='outro',title='Your week',facts=[dict(label='Fact '+str(i),value=i) for i in range(6)],tries=['Ask for one example.','Define done.','Keep a short checklist.'],footer='Reactions are proxies, not grades.'),
    ]


def default_deck():
    by_type={s['type']:s for s in components()}
    slides=[copy.deepcopy(by_type[k]) for k in ('cold','bignum','lineup','coach','ranking','heatmap','coach','tally','coach','archetype','coach','outro')]
    for i,word in [(6,'Define done.'),(8,'Keep a short checklist.'),(10,'Share the why.')]:
        slides[i]['try']=word
        slides[i]['kind']='win' if i==6 else 'tweak'
    return dict(schema_version=1,profile='default-12',seed=7,title='Synthetic Agent Retro',slides=slides)
