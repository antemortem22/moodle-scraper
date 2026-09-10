"""Paleta centralizada: cambiar estos valores ajusta toda la interfaz."""
from tkinter import ttk, PhotoImage

PALETTE = dict(bg='#17151C', panel='#211C2A', accent='#7C4DFF', soft='#9B7BFF',
               deep='#4D2C91', text='#F3F0F7', muted='#B8B1C5', border='#39313F',
               success='#7ED6A5', error='#F08A8A')


def apply_theme(root):
    p = PALETTE
    style = ttk.Style(root)
    style.theme_use('clam')
    root.configure(background=p['bg'])
    style.configure('.', background=p['panel'], foreground=p['text'], font=('Segoe UI', 10), bordercolor=p['border'], lightcolor=p['border'], darkcolor=p['border'])
    style.configure('Root.TFrame', background=p['bg'])
    style.configure('Title.TLabel', font=('Segoe UI', 15, 'bold'))
    style.configure('Muted.TLabel', foreground=p['muted'])
    style.configure('TButton', padding=(12, 7), background=p['panel'], bordercolor=p['border'])
    style.map('TButton', background=[('active',p['deep'])], foreground=[('disabled',p['muted'])])
    style.configure('Accent.TButton', background=p['accent'], foreground=p['text'], font=('Segoe UI',10,'bold'))
    style.map('Accent.TButton', background=[('disabled',p['border']),('active',p['soft'])])
    style.configure('TCheckbutton', padding=(3,5), indicatorbackground=p['bg'], indicatorforeground=p['soft'])
    style.map('TCheckbutton', foreground=[('disabled',p['muted'])], background=[('active',p['panel'])],
              indicatorbackground=[('selected',p['accent']),('disabled',p['border'])])
    style.configure('TCombobox', fieldbackground=p['bg'], background=p['border'], arrowcolor=p['soft'], padding=7)
    style.map('TCombobox', fieldbackground=[('readonly',p['bg']),('disabled',p['panel'])],
              foreground=[('readonly',p['text']),('disabled',p['muted'])], selectbackground=[('readonly',p['deep'])])
    style.configure('Treeview', background=p['panel'], fieldbackground=p['panel'], foreground=p['text'], rowheight=29, borderwidth=0)
    style.map('Treeview', background=[('selected',p['deep'])], foreground=[('selected',p['text'])])
    style.configure('Horizontal.TProgressbar', background=p['accent'], troughcolor=p['bg'], borderwidth=0)
    style.configure('TScrollbar', background=p['border'], troughcolor=p['panel'], arrowcolor=p['muted'])
    for name in ('Vertical.TScrollbar', 'Horizontal.TScrollbar'):
        style.configure(name, background=p['border'], troughcolor=p['panel'], arrowcolor=p['muted'], bordercolor=p['border'], lightcolor=p['border'], darkcolor=p['border'])
        style.map(name, background=[('active',p['deep']),('pressed',p['accent'])])
    style.configure('TPanedwindow', background=p['bg'])
    root.option_add('*TCombobox*Listbox.background',p['panel'])
    root.option_add('*TCombobox*Listbox.foreground',p['text'])
    root.option_add('*TCombobox*Listbox.selectBackground',p['deep'])
    # Explicit square and tick, independent of the theme's default indicator.
    images = []
    for selected, disabled in ((False, False), (True, False), (False, True), (True, True)):
        icon = PhotoImage(master=root, width=26, height=20)
        icon.put(p['border'] if disabled else p['soft'], to=(1, 1, 19, 19))
        icon.put(p['deep'] if selected and disabled else p['accent'] if selected else p['bg'], to=(3, 3, 17, 17))
        ink = p['muted'] if disabled else p['text']
        if selected:
            for x, y in ((5, 9), (6, 10), (7, 11), (8, 12), (9, 11), (10, 10), (11, 9), (12, 8), (13, 7), (14, 6)):
                icon.put(ink, to=(x, y, x+2, y+2))
        elif disabled:
            icon.put(ink, to=(6, 9, 14, 11))
        images.append(icon)
    root.section_indicators = images  # Tk images need a live Python reference.
    style.element_create('Section.indicator', 'image', images[0],
                         ('disabled', 'selected', images[3]), ('disabled', images[2]),
                         ('selected', images[1]), sticky='w')
    style.layout('Section.TCheckbutton', [('Checkbutton.padding', {'sticky': 'nswe', 'children': [
        ('Section.indicator', {'side': 'left', 'sticky': 'w'}),
        ('Checkbutton.focus', {'side': 'left', 'sticky': 'w', 'children': [
            ('Checkbutton.label', {'sticky': 'nswe'})]})]})])
    return style
