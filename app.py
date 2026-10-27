"""KeyPressor — a visual desktop workflow studio."""
from __future__ import annotations

import json
import queue
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    from workflow_engine import Workflow, WorkflowRunner, DEFAULT_WORKFLOW
except Exception:
    Workflow = WorkflowRunner = None
    DEFAULT_WORKFLOW = []

ROOT = Path(__file__).resolve().parent
COLORS = {"bg":"#0B1020","surface":"#11182B","surface2":"#151F36","surface3":"#1B2742","line":"#263453","text":"#EDF2FF","muted":"#8291B5","violet":"#8B5CF6","violet2":"#A78BFA","cyan":"#2DD4BF","amber":"#F6C453","red":"#F87171"}
ACTION_META = {"loop":("↻","Loop","Repeat until stopped"),"delay":("◷","Delay","Pause for a precise duration"),"type":("⌨","Type text","Insert text at the active cursor"),"move":("⌖","Move cursor","Move to a screen point or OCR target"),"click":("◉","Click","Click a mouse button"),"hotkey":("⌘","Hotkey","Press a key combination"),"script":("{}","Run script","Run a Python snippet")}

class KeyPressorApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("KeyPressor · workflow studio"); self.geometry("1440x900"); self.minsize(1100,700); self.configure(bg=COLORS["bg"]); self.protocol("WM_DELETE_WINDOW",self.on_close)
        self.workflow=self._new_workflow(); self.selected_index=0; self.runner=None; self.events=queue.Queue(); self.file_var=tk.StringVar(value="Untitled workflow"); self.status_var=tk.StringVar(value="Ready to compose"); self.runtime_var=tk.StringVar(value="Idle"); self.steps_count=tk.StringVar()
        self._styles(); self._layout(); self.render_steps(); self.render_inspector(); self.after(120,self._drain)
    def _new_workflow(self):
        data={"name":"Untitled workflow","steps":DEFAULT_WORKFLOW or [{"type":"loop","label":"Loop until stopped","stop_hotkey":"Ctrl + Alt + 5"},{"type":"delay","label":"Wait 2 seconds","seconds":2},{"type":"type","label":"Type text","text":"AAAA","paste":True},{"type":"move","label":"Move cursor","x":640,"y":420,"ocr":True,"ocr_text":""},{"type":"click","label":"Click mouse","button":"left","clicks":1},{"type":"hotkey","label":"Press shortcut","keys":["Ctrl","Enter"]}]}
        return data
    def _steps(self): return self.workflow.get("steps",[]) if isinstance(self.workflow,dict) else self.workflow.steps
    def _data(self,s): return s if isinstance(s,dict) else (s.to_dict() if hasattr(s,"to_dict") else vars(s))
    def _styles(self):
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except tk.TclError:pass
        s.configure("KP.TButton",background=COLORS["surface2"],foreground=COLORS["text"],borderwidth=0,padding=(12,7),font=("Helvetica",10)); s.map("KP.TButton",background=[("active",COLORS["surface3"])])
        s.configure("Accent.TButton",background=COLORS["violet"],foreground="white",borderwidth=0,padding=(15,8),font=("Helvetica",10,"bold")); s.map("Accent.TButton",background=[("active",COLORS["violet2"])])
        s.configure("KP.TEntry",fieldbackground=COLORS["surface3"],background=COLORS["surface3"],foreground=COLORS["text"],borderwidth=0,padding=7)
        s.configure("KP.TCombobox",fieldbackground=COLORS["surface3"],background=COLORS["surface3"],foreground=COLORS["text"],borderwidth=0,padding=6)
        s.configure("KP.Horizontal.TProgressbar",troughcolor=COLORS["surface3"],background=COLORS["cyan"],borderwidth=0,thickness=5)
    def _button(self,p,text,cmd,accent=False): return ttk.Button(p,text=text,command=cmd,style="Accent.TButton" if accent else "KP.TButton",cursor="hand2")
    def _layout(self):
        top=tk.Frame(self,bg=COLORS["bg"],height=72); top.pack(fill="x"); top.pack_propagate(False)
        brand=tk.Frame(top,bg=COLORS["bg"]); brand.pack(side="left",padx=28); tk.Label(brand,text="✦",fg=COLORS["cyan"],bg=COLORS["bg"],font=("Helvetica",22,"bold")).pack(side="left",padx=(0,10)); tk.Label(brand,text="KeyPressor",fg=COLORS["text"],bg=COLORS["bg"],font=("Helvetica",19,"bold")).pack(side="left"); tk.Label(brand,text="  /  flow studio",fg=COLORS["muted"],bg=COLORS["bg"],font=("Helvetica",10)).pack(side="left",pady=(7,0))
        tools=tk.Frame(top,bg=COLORS["bg"]); tools.pack(side="right",padx=24); self._button(tools,"Save",self.save).pack(side="left",padx=4); self._button(tools,"Open",self.open).pack(side="left",padx=4); self._button(tools,"Preview",lambda:self.run(True)).pack(side="left",padx=4); self._button(tools,"Run workflow",lambda:self.run(False),True).pack(side="left",padx=(12,0))
        body=tk.Frame(self,bg=COLORS["bg"]); body.pack(fill="both",expand=True,padx=20,pady=(0,20)); body.columnconfigure(1,weight=1); body.rowconfigure(0,weight=1); self._sidebar(body); self._flow(body); self._inspector(body); self._status()
    def _sidebar(self,parent):
        side=tk.Frame(parent,bg=COLORS["surface"],width=215); side.grid(row=0,column=0,sticky="nsew",padx=(0,16)); side.grid_propagate(False); tk.Label(side,text="ACTION LIBRARY",fg=COLORS["muted"],bg=COLORS["surface"],font=("Helvetica",9,"bold")).pack(anchor="w",padx=18,pady=(22,12))
        for kind,(icon,title,desc) in ACTION_META.items():
            row=tk.Frame(side,bg=COLORS["surface"],cursor="hand2"); row.pack(fill="x",padx=10,pady=2); tk.Label(row,text=icon,width=3,fg=COLORS["violet2"] if kind=="loop" else COLORS["cyan"],bg=COLORS["surface"],font=("Helvetica",12)).pack(side="left",padx=(8,2),pady=5); txt=tk.Frame(row,bg=COLORS["surface"]); txt.pack(side="left",fill="x",expand=True); tk.Label(txt,text=title,fg=COLORS["text"],bg=COLORS["surface"],font=("Helvetica",10,"bold"),anchor="w").pack(fill="x"); tk.Label(txt,text=desc,fg=COLORS["muted"],bg=COLORS["surface"],font=("Helvetica",8),anchor="w").pack(fill="x")
            for w in (row,txt): w.bind("<Button-1>",lambda e,k=kind:self.add_step(k))
        tk.Frame(side,bg=COLORS["line"],height=1).pack(fill="x",padx=18,pady=(22,16)); tk.Label(side,text="WORKSPACE",fg=COLORS["muted"],bg=COLORS["surface"],font=("Helvetica",9,"bold")).pack(anchor="w",padx=18,pady=(0,10))
        for label,cmd in [("⌗  Keyboard map",self.keyboard_map),("⌁  Run history",self.history),("⚙  Preferences",self.preferences)]: tk.Button(side,text=label,command=cmd,anchor="w",bd=0,bg=COLORS["surface"],fg=COLORS["muted"],activebackground=COLORS["surface2"],activeforeground=COLORS["text"],font=("Helvetica",10),padx=16,pady=8).pack(fill="x",padx=4)
        tk.Label(side,text="Aplus-Nexus",fg=COLORS["violet2"],bg=COLORS["surface"],font=("Helvetica",9,"bold")).pack(side="bottom",anchor="w",padx=18,pady=16)
    def _flow(self,parent):
        c=tk.Frame(parent,bg=COLORS["bg"]); c.grid(row=0,column=1,sticky="nsew"); c.rowconfigure(2,weight=1); c.columnconfigure(0,weight=1); h=tk.Frame(c,bg=COLORS["bg"]); h.grid(row=0,column=0,sticky="ew",pady=(0,17)); tk.Label(h,textvariable=self.file_var,fg=COLORS["text"],bg=COLORS["bg"],font=("Helvetica",19,"bold")).pack(side="left"); tk.Label(h,text="  /  draft",fg=COLORS["muted"],bg=COLORS["bg"],font=("Helvetica",10)).pack(side="left",pady=(7,0)); tk.Label(h,text="Ctrl + Alt + 5  stops the run",fg=COLORS["muted"],bg=COLORS["bg"],font=("Helvetica",9)).pack(side="right",pady=(7,0))
        shell=tk.Frame(c,bg=COLORS["surface"],highlightbackground=COLORS["line"],highlightthickness=1); shell.grid(row=2,column=0,sticky="nsew"); shell.rowconfigure(1,weight=1); shell.columnconfigure(0,weight=1); head=tk.Frame(shell,bg=COLORS["surface"],height=58); head.grid(row=0,column=0,sticky="ew"); head.pack_propagate(False); tk.Label(head,text="Workflow",fg=COLORS["text"],bg=COLORS["surface"],font=("Helvetica",11,"bold")).pack(side="left",padx=20); tk.Label(head,textvariable=self.steps_count,fg=COLORS["muted"],bg=COLORS["surface"],font=("Helvetica",9)).pack(side="left"); self._button(head,"+ Add step",lambda:self.add_step("delay")).pack(side="right",padx=15); tk.Frame(shell,bg=COLORS["line"],height=1).grid(row=0,column=0,sticky="sew",pady=(57,0))
        wrap=tk.Frame(shell,bg=COLORS["surface"]); wrap.grid(row=1,column=0,sticky="nsew"); wrap.rowconfigure(0,weight=1); wrap.columnconfigure(0,weight=1); self.canvas=tk.Canvas(wrap,bg=COLORS["surface"],bd=0,highlightthickness=0); self.canvas.grid(row=0,column=0,sticky="nsew"); sb=ttk.Scrollbar(wrap,orient="vertical",command=self.canvas.yview); sb.grid(row=0,column=1,sticky="ns"); self.canvas.configure(yscrollcommand=sb.set); self.step_inner=tk.Frame(self.canvas,bg=COLORS["surface"]); self.window=self.canvas.create_window((0,0),window=self.step_inner,anchor="nw"); self.step_inner.bind("<Configure>",lambda e:self.canvas.configure(scrollregion=self.canvas.bbox("all"))); self.canvas.bind("<Configure>",lambda e:self.canvas.itemconfigure(self.window,width=e.width))
    def _inspector(self,parent):
        self.right=tk.Frame(parent,bg=COLORS["surface"],width=306); self.right.grid(row=0,column=2,sticky="nsew",padx=(16,0)); self.right.grid_propagate(False); tk.Label(self.right,text="INSPECTOR",fg=COLORS["muted"],bg=COLORS["surface"],font=("Helvetica",9,"bold")).pack(anchor="w",padx=20,pady=(22,14)); self.inspector=tk.Frame(self.right,bg=COLORS["surface"]); self.inspector.pack(fill="both",expand=True,padx=20)
    def _status(self):
        b=tk.Frame(self,bg=COLORS["surface2"],height=38); b.pack(side="bottom",fill="x"); b.pack_propagate(False); tk.Label(b,textvariable=self.status_var,fg=COLORS["muted"],bg=COLORS["surface2"],font=("Helvetica",9)).pack(side="left",padx=22); tk.Label(b,textvariable=self.runtime_var,fg=COLORS["cyan"],bg=COLORS["surface2"],font=("Helvetica",9,"bold")).pack(side="right",padx=22); self.progress=ttk.Progressbar(b,style="KP.Horizontal.TProgressbar",mode="determinate",length=120); self.progress.pack(side="right",padx=(0,12))
    def render_steps(self):
        for w in self.step_inner.winfo_children(): w.destroy()
        steps=self._steps(); self.steps_count.set(f"{len(steps)} steps")
        for i,s in enumerate(steps):
            d=self._data(s); k=d.get("type","delay"); selected=i==self.selected_index; bg=COLORS["surface3"] if selected else COLORS["surface"]; accent=COLORS["violet"] if k=="loop" else COLORS["cyan"] if k in ("type","hotkey") else COLORS["amber"] if k=="delay" else COLORS["violet2"]; row=tk.Frame(self.step_inner,bg=bg,height=73,cursor="hand2"); row.pack(fill="x",padx=18,pady=(10 if i==0 else 4,4)); row.pack_propagate(False); tk.Frame(row,bg=accent,width=3).pack(side="left",fill="y"); tk.Label(row,text=f"{i+1:02}",fg=COLORS["muted"],bg=bg,font=("Helvetica",9,"bold"),width=4).pack(side="left"); tk.Label(row,text=ACTION_META.get(k,("•",k,""))[0],fg=accent,bg=bg,font=("Helvetica",17),width=3).pack(side="left"); text=tk.Frame(row,bg=bg); text.pack(side="left",fill="both",expand=True,pady=14); tk.Label(text,text=d.get("label",ACTION_META.get(k,("",k,""))[1]),fg=COLORS["text"],bg=bg,font=("Helvetica",10,"bold"),anchor="w").pack(fill="x"); tk.Label(text,text=self.summary(d),fg=COLORS["muted"],bg=bg,font=("Helvetica",9),anchor="w").pack(fill="x")
            if selected:
                acts=tk.Frame(row,bg=bg); acts.pack(side="right",padx=10); [tk.Button(acts,text=t,command=cmd,bd=0,bg=bg,fg=COLORS["red"] if t=="×" else COLORS["muted"],activebackground=bg,font=("Helvetica",14 if t=="×" else 11)).pack(side="left") for t,cmd in [("↑",lambda i=i:self.move(i,-1)),("↓",lambda i=i:self.move(i,1)),("×",lambda i=i:self.delete(i))]]
            for w in (row,text): w.bind("<Button-1>",lambda e,i=i:self.select(i))
    def summary(self,d):
        k=d.get("type"); return {"loop":f"Until {d.get('stop_hotkey','Ctrl + Alt + 5')} is pressed","delay":f"{d.get('seconds',2)} seconds","type":repr(d.get('text','AAAA'))[:42],"move":f"{d.get('x',640)}, {d.get('y',420)} · {d.get('target','screen point')}","click":f"{d.get('button','left').title()} button · {d.get('clicks',1)} click","hotkey":" + ".join(d.get('keys',['Ctrl','Enter'])),"script":"Python snippet · run in worker"}.get(k,"Ready")
    def render_inspector(self):
        if not hasattr(self,"inspector"): return
        for w in self.inspector.winfo_children(): w.destroy()
        steps=self._steps()
        if not steps:return
        d=self._data(steps[self.selected_index]); k=d.get("type","delay"); self.label("Step name"); name=tk.StringVar(value=d.get("label",ACTION_META.get(k,("",k,""))[1])); e=ttk.Entry(self.inspector,textvariable=name,style="KP.TEntry"); e.pack(fill="x",pady=(0,16)); e.bind("<FocusOut>",lambda e:self.update("label",name.get())); self.label("Action"); tk.Label(self.inspector,text=ACTION_META.get(k,("",k,""))[1],fg=COLORS["cyan"],bg=COLORS["surface"],font=("Helvetica",12,"bold")).pack(anchor="w",pady=(0,20))
        fields={"loop":[("Stop shortcut","stop_hotkey","Ctrl + Alt + 5"),("Iterations (optional)","max_iterations","")],"delay":[("Seconds","seconds","2")],"type":[("Text to type","text","AAAA")],"move":[("X position","x","640"),("Y position","y","420"),("OCR target (optional)","ocr_text","")],"click":[("Button","button","left"),("Clicks","clicks","1"),("Interval","interval","0.08")],"hotkey":[("Keys","keys_text","Ctrl + Enter")],"script":[("Python","script","# available: pyautogui, time\n")]}.get(k,[])
        for label,key,default in fields:self.field(label,d,key,default,multiline=k=="script")
        if k in ("type","move"): self.check("Try OCR / clipboard when available" if k=="move" else "Use clipboard paste",d,"ocr" if k=="move" else "paste",True)
        tk.Frame(self.inspector,bg=COLORS["line"],height=1).pack(fill="x",pady=(20,16)); self.label("RUN SAFETY"); tk.Label(self.inspector,text="Ctrl + Alt + 5 always stops the active run. Preview mode never touches your cursor.",fg=COLORS["muted"],bg=COLORS["surface"],font=("Helvetica",9),wraplength=260,justify="left").pack(anchor="w",pady=(8,0))
    def label(self,text):tk.Label(self.inspector,text=text,fg=COLORS["muted"],bg=COLORS["surface"],font=("Helvetica",9,"bold")).pack(anchor="w",pady=(0,6))
    def field(self,label,d,key,default,multiline=False):
        self.label(label); val=d.get(key,default); val=" + ".join(d.get("keys",["Ctrl","Enter"])) if key=="keys_text" and not val else val
        if multiline:
            box=tk.Text(self.inspector,height=6,bg=COLORS["surface3"],fg=COLORS["text"],insertbackground=COLORS["text"],bd=0,padx=8,pady=7,font=("Menlo",10),wrap="word"); box.insert("1.0",str(val)); box.pack(fill="x",pady=(0,14)); box.bind("<FocusOut>",lambda e:self.update(key,box.get("1.0","end-1c")))
        else:
            var=tk.StringVar(value=str(val)); e=ttk.Entry(self.inspector,textvariable=var,style="KP.TEntry"); e.pack(fill="x",pady=(0,14)); e.bind("<FocusOut>",lambda e:self.update(key,var.get()))
    def check(self,label,d,key,default):
        var=tk.BooleanVar(value=bool(d.get(key,default))); tk.Checkbutton(self.inspector,text=label,variable=var,command=lambda:self.update(key,var.get()),bg=COLORS["surface"],fg=COLORS["muted"],activebackground=COLORS["surface"],selectcolor=COLORS["surface3"],bd=0,font=("Helvetica",9),anchor="w").pack(fill="x",pady=(0,8))
    def select(self,i): self.selected_index=i; self.render_steps(); self.render_inspector()
    def add_step(self,k):
        d={"loop":{"type":"loop","label":"Loop until stopped","stop_hotkey":"Ctrl + Alt + 5"},"delay":{"type":"delay","label":"Wait a little","seconds":2},"type":{"type":"type","label":"Type text","text":"AAAA","paste":True},"move":{"type":"move","label":"Move cursor","x":640,"y":420,"ocr":True,"ocr_text":""},"click":{"type":"click","label":"Click mouse","button":"left","clicks":1,"interval":0.08},"hotkey":{"type":"hotkey","label":"Press shortcut","keys":["Ctrl","Enter"],"keys_text":"Ctrl + Enter"},"script":{"type":"script","label":"Run Python snippet","script":"# available: pyautogui, time\n"}}.get(k); self._steps().append(d); self.selected_index=len(self._steps())-1; self.render_steps(); self.render_inspector(); self.status_var.set(f"Added {ACTION_META[k][1]}")
    def update(self,key,val):
        d=self._data(self._steps()[self.selected_index]);
        if key in ("seconds","x","y","clicks","interval"):
            try: val=float(val) if "." in str(val) else int(val)
            except: pass
        if key=="keys_text":d["keys"]=[x.strip() for x in str(val).replace("+",",").split(",") if x.strip()]
        d[key]=val; self.render_steps()
    def move(self,i,delta):
        a=self._steps(); n=i+delta
        if 0<=n<len(a): a[i],a[n]=a[n],a[i]; self.selected_index=n; self.render_steps(); self.render_inspector()
    def delete(self,i):
        a=self._steps()
        if len(a)<=1:return
        a.pop(i); self.selected_index=max(0,min(i,len(a)-1)); self.render_steps(); self.render_inspector()
    def serial(self): return self.workflow if isinstance(self.workflow,dict) else self.workflow.to_dict()
    def save(self):
        p=filedialog.asksaveasfilename(defaultextension=".kpflow",filetypes=[("KeyPressor workflow","*.kpflow"),("JSON","*.json")]);
        if p: Path(p).write_text(json.dumps(self.serial(),indent=2,ensure_ascii=False),encoding="utf-8"); self.file_var.set(Path(p).stem); self.status_var.set(f"Saved {Path(p).name}")
    def open(self):
        p=filedialog.askopenfilename(filetypes=[("KeyPressor workflow","*.kpflow"),("JSON","*.json")]);
        if p:
            try:self.workflow=json.loads(Path(p).read_text(encoding="utf-8")); self.selected_index=0; self.file_var.set(Path(p).stem); self.render_steps(); self.render_inspector(); self.status_var.set(f"Opened {Path(p).name}")
            except Exception as e:messagebox.showerror("Could not open",str(e))
    def run(self,preview=False):
        if self.runner and getattr(self.runner,"is_running",lambda:False)(): self.runner.stop(); return
        if not WorkflowRunner:self.status_var.set("Workflow engine unavailable"); return
        self.status_var.set("Previewing workflow…" if preview else "Running workflow…"); self.runtime_var.set("Preview" if preview else "Live"); self.progress["value"]=0; self.runner=WorkflowRunner(self.serial(),preview=preview,event_queue=self.events); self.runner.start()
    def _drain(self):
        try:
            while True:
                ev,p=self.events.get_nowait();
                if ev=="progress":self.progress["value"]=p
                elif ev=="log":self.status_var.set(str(p))
                elif ev=="done":self.status_var.set("Workflow completed");self.runtime_var.set("Idle");self.progress["value"]=100
                elif ev=="stopped":self.status_var.set("Workflow stopped");self.runtime_var.set("Idle")
                elif ev=="error":self.status_var.set(f"Error: {p}");self.runtime_var.set("Needs attention")
        except queue.Empty:pass
        self.after(120,self._drain)
    def keyboard_map(self):messagebox.showinfo("Keyboard map","Ctrl + Alt + 5\nStops the active workflow immediately.")
    def history(self):messagebox.showinfo("Run history","Run history will appear after the first saved run.")
    def preferences(self):messagebox.showinfo("Preferences","Preview mode is safe by default. Optional integrations are detected at launch.")
    def on_close(self):
        if self.runner:self.runner.stop()
        self.destroy()

if __name__=="__main__":KeyPressorApp().mainloop()
