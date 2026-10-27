"""PySide6 UI for KeyPro's visual workflow studio."""
from __future__ import annotations
import copy, json, queue, sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QDoubleSpinBox, QVBoxLayout,
    QWidget, QProgressBar, QInputDialog, QMenu,
)

from workflow_engine import DEFAULT_WORKFLOW, WorkflowRunner

ROOT = Path(__file__).resolve().parent
C = {"bg":"#0B1020","surface":"#11182B","surface2":"#151F36","surface3":"#1B2742","line":"#263453","text":"#EDF2FF","muted":"#8291B5","violet":"#8B5CF6","violet2":"#A78BFA","cyan":"#2DD4BF","amber":"#F6C453","red":"#F87171"}
META = {
    "loop": ("↻", "Loop", "Repeat until stopped", C["violet2"]),
    "delay": ("◷", "Delay", "Pause for a duration", C["amber"]),
    "type": ("⌨", "Type text", "Insert into active field", C["cyan"]),
    "move": ("⌖", "Move cursor", "Point or OCR target", C["violet2"]),
    "click": ("◉", "Click", "Mouse button action", C["violet2"]),
    "hotkey": ("⌘", "Hotkey", "Press a key combination", C["cyan"]),
    "script": ("{}", "Run script", "Run a Python snippet", C["cyan"]),
}

STYLE = f"""
* {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: {C['text']}; }}
QMainWindow, QWidget {{ background: {C['bg']}; }}
QLabel {{ background: transparent; }}
QLabel {{ background: transparent; }}
QFrame#panel, QFrame#workflowCard {{ background: {C['surface']}; border: 1px solid {C['line']}; border-radius: 12px; }}
QLabel#brand {{ font-size: 24px; font-weight: 700; }}
QLabel#brandMark {{ color: {C['cyan']}; font-size: 28px; font-weight: 700; }}
QLabel#muted, QLabel[muted="true"] {{ color: {C['muted']}; }}
QLabel#eyebrow {{ color: {C['muted']}; font-size: 11px; font-weight: 700; letter-spacing: 2px; }}
QLabel#pageTitle {{ font-size: 24px; font-weight: 700; }}
QPushButton {{ background: {C['surface2']}; border: 0; border-radius: 8px; padding: 9px 14px; color: {C['text']}; }}
QPushButton:hover {{ background: {C['surface3']}; }}
QPushButton#run {{ background: {C['violet']}; color: white; font-weight: 700; padding: 10px 18px; }}
QPushButton#run:hover {{ background: {C['violet2']}; }}
QPushButton#workflowMenu {{ background: {C['surface2']}; color: {C['text']}; padding: 8px 12px; }}
QPushButton#action {{ text-align: left; background: transparent; padding: 8px 10px; border-radius: 8px; }}
QPushButton#action:hover {{ background: {C['surface2']}; }}
QLabel#actionIcon {{ font-size: 20px; color: {C['cyan']}; min-width: 26px; }}
QLabel#actionTitle {{ font-size: 14px; font-weight: 700; }}
QLabel#actionDesc, QLabel#stepDesc {{ color: {C['muted']}; font-size: 12px; }}
QFrame#step {{ background: {C['surface2']}; border-radius: 9px; }}
QFrame#step[selected="true"] {{ background: {C['surface3']}; border: 1px solid {C['line']}; }}
QFrame#stepAccent {{ border: 0; border-radius: 2px; }}
QLabel#stepNo {{ color: {C['muted']}; font-size: 11px; font-weight: 700; min-width: 28px; }}
QLabel#stepIcon {{ font-size: 20px; min-width: 34px; }}
QLabel#stepTitle {{ font-size: 14px; font-weight: 700; }}
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{ background: {C['surface3']}; border: 0; border-radius: 7px; padding: 9px; color: {C['text']}; selection-background-color: {C['violet']}; }}
QComboBox QAbstractItemView {{ background: {C['surface3']}; color: {C['text']}; selection-background-color: {C['violet']}; }}
QCheckBox {{ color: {C['muted']}; spacing: 8px; }}
QScrollArea {{ border: 0; background: transparent; }}
QProgressBar {{ background: {C['surface3']}; border: 0; border-radius: 4px; height: 6px; }}
QProgressBar::chunk {{ background: {C['cyan']}; border-radius: 4px; }}
QStatusBar {{ background: {C['surface2']}; color: {C['muted']}; }}
QSplitter::handle {{ background: {C['bg']}; }}
"""


def icon_pixmap() -> QPixmap:
    path = ROOT / "assets" / "keypro-logo.png"
    if path.exists(): return QPixmap(str(path))
    return QPixmap()

class StepRow(QFrame):
    clicked = Signal(object)
    def __init__(self, index: int, data: dict[str, Any], selected: bool):
        super().__init__(); self.index = index; self.data = data; self.setObjectName("step"); self.setProperty("selected", selected); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setMinimumHeight(76)
        layout = QHBoxLayout(self); layout.setContentsMargins(8, 10, 14, 10); layout.setSpacing(10)
        accent = QFrame(); accent.setObjectName("stepAccent"); accent.setFixedWidth(4); accent.setStyleSheet(f"background: {META.get(data.get('type','delay'), ('','','',C['cyan']))[3]};"); layout.addWidget(accent)
        no = QLabel(f"{index + 1:02d}"); no.setObjectName("stepNo"); layout.addWidget(no)
        kind = data.get("type", "delay"); icon, _, _, color = META.get(kind, ("•", kind.title(), "", C["cyan"]))
        ico = QLabel(icon); ico.setObjectName("stepIcon"); ico.setStyleSheet(f"color: {color};"); layout.addWidget(ico)
        col = QVBoxLayout(); col.setSpacing(2)
        title = QLabel(data.get("label") or META.get(kind, ("", kind, "", C["cyan"]))[1]); title.setObjectName("stepTitle")
        desc = QLabel(self.summary(data)); desc.setObjectName("stepDesc")
        col.addWidget(title); col.addWidget(desc); layout.addLayout(col, 1)
        if selected:
            for txt, signal in [("↑", -1), ("↓", 1), ("×", 99)]:
                b = QPushButton(txt); b.setFixedWidth(24); b.setStyleSheet(f"QPushButton {{ background: transparent; color: {C['red'] if txt == '×' else C['muted']}; font-size: 15px; padding: 2px; }} QPushButton:hover {{ color: {C['text']}; }}")
                b.clicked.connect(lambda checked=False, d=signal: self.clicked.emit(("delete", self.index) if d == 99 else ("move", self.index, d))); layout.addWidget(b)
        self.setMouseTracking(True)
    def summary(self, d):
        k=d.get("type")
        if k == "loop": return f"Until {d.get('stop_hotkey','Ctrl + Alt + 5')} is pressed"
        if k == "delay": return f"{d.get('seconds',2)} seconds"
        if k == "type": return repr(d.get("text", "AAAA"))
        if k == "move": return f"{d.get('x',640)}, {d.get('y',420)} · {d.get('target','screen point')}"
        if k == "click": return f"{d.get('button','left').title()} button · {d.get('clicks',1)} click"
        if k == "hotkey": return " + ".join(d.get('keys', ['Ctrl','Enter']))
        if k == "script": return "Python snippet · run in worker"
        return "Ready"
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.clicked.emit(("select", self.index))
        super().mousePressEvent(event)

class KeyProWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("KeyPro · workflow studio"); self.resize(1440, 900); self.setMinimumSize(1120, 700); self.setStyleSheet(STYLE)
        initial = {"name":"Submit form repeatedly", "steps": [dict(x) for x in DEFAULT_WORKFLOW]}
        self.workflows = {initial["name"]: initial}; self.active_workflow = initial["name"]; self.workflow = initial
        self.selected = 0; self.runner = None; self.events = queue.Queue(); self.build_ui(); self.render_steps(); self.render_inspector(); self.timer = QTimer(self); self.timer.timeout.connect(self.drain_events); self.timer.start(100)
    def build_ui(self):
        root = QWidget(); self.setCentralWidget(root); outer = QVBoxLayout(root); outer.setContentsMargins(20, 16, 20, 0); outer.setSpacing(14)
        top = QHBoxLayout(); top.setSpacing(10); mark=QLabel("✦"); mark.setObjectName("brandMark"); top.addWidget(mark); brand=QLabel("KeyPro"); brand.setObjectName("brand"); top.addWidget(brand); flow=QLabel("/ flow studio"); flow.setProperty("muted", True); top.addWidget(flow)
        self.workflow_menu = QMenu(self)
        self.workflow_menu.aboutToShow.connect(self.refresh_workflow_menu)
        self.workflow_menu.setStyleSheet(f"QMenu {{ background:{C['surface']}; border:1px solid {C['line']}; padding:6px; }} QMenu::item {{ padding:8px 18px; }} QMenu::item:selected {{ background:{C['surface3']}; }}")
        self.workflow_button = QPushButton("Workflows ▾"); self.workflow_button.setObjectName("workflowMenu"); self.workflow_button.setMenu(self.workflow_menu); top.addWidget(self.workflow_button); top.addStretch();
        self.save_btn=self.button("Save", self.save); self.open_btn=self.button("Open", self.open); self.preview_btn=self.button("Preview", lambda: self.run(True)); self.run_btn=self.button("Run workflow", lambda: self.run(False), "run")
        for b in (self.save_btn,self.open_btn,self.preview_btn,self.run_btn): top.addWidget(b)
        outer.addLayout(top)
        body=QHBoxLayout(); body.setSpacing(20); outer.addLayout(body,1)
        body.addWidget(self.sidebar(),0); body.addWidget(self.center(),1); body.addWidget(self.inspector(),0)
        self.statusBar().showMessage("Ready to compose"); self.runtime_label=QLabel("Idle"); self.runtime_label.setStyleSheet(f"color:{C['cyan']}; font-weight:700;"); self.statusBar().addPermanentWidget(self.runtime_label); self.progress=QProgressBar(); self.progress.setRange(0,100); self.progress.setFixedWidth(130); self.statusBar().addPermanentWidget(self.progress)
    def button(self,text,slot,obj=None):
        b=QPushButton(text); b.clicked.connect(slot); b.setObjectName(obj or ""); return b
    def refresh_workflow_menu(self):
        self.workflow_menu.clear()
        self.workflow_menu.addAction("New workflow", self.new_workflow)
        self.workflow_menu.addAction("Duplicate active", self.duplicate_workflow)
        self.workflow_menu.addAction("Rename active", self.rename_workflow)
        self.workflow_menu.addAction("Delete active", self.delete_workflow)
        self.workflow_menu.addSeparator()
        for name in self.workflows:
            prefix = "✓  " if name == self.active_workflow else "   "
            self.workflow_menu.addAction(prefix + name, lambda checked=False, n=name: self.switch_workflow(n))
    def switch_workflow(self, name):
        if name not in self.workflows: return
        self.active_workflow = name; self.workflow = self.workflows[name]; self.selected = 0
        self.file_title.setText(name); self.render_steps(); self.render_inspector(); self.statusBar().showMessage(f"Switched to {name}")
    def new_workflow(self):
        name, ok = QInputDialog.getText(self, "New workflow", "Workflow name:", text="Untitled workflow")
        name = name.strip()
        if not ok or not name: return
        base = name; suffix = 2
        while name in self.workflows:
            name = f"{base} {suffix}"; suffix += 1
        data = {"name": name, "steps": [{"type":"delay", "label":"Wait a little", "seconds":2}]}
        self.workflows[name] = data; self.switch_workflow(name)
    def duplicate_workflow(self):
        base = f"Copy of {self.active_workflow}"; name = base; suffix = 2
        while name in self.workflows:
            name = f"{base} {suffix}"; suffix += 1
        data = copy.deepcopy(self.workflow); data["name"] = name; self.workflows[name] = data; self.switch_workflow(name)
    def rename_workflow(self):
        name, ok = QInputDialog.getText(self, "Rename workflow", "Workflow name:", text=self.active_workflow)
        name = name.strip()
        if not ok or not name or name == self.active_workflow: return
        if name in self.workflows:
            QMessageBox.warning(self, "Workflow exists", "Choose a different workflow name."); return
        data = self.workflows.pop(self.active_workflow); data["name"] = name; self.workflows[name] = data; self.switch_workflow(name)
    def delete_workflow(self):
        if len(self.workflows) <= 1:
            QMessageBox.information(self, "Keep one workflow", "KeyPro needs at least one workflow."); return
        answer = QMessageBox.question(self, "Delete workflow", f"Delete '{self.active_workflow}'?")
        if answer != QMessageBox.StandardButton.Yes: return
        old = self.active_workflow; self.workflows.pop(old); self.switch_workflow(next(iter(self.workflows)))
    def sidebar(self):
        panel=QFrame(); panel.setObjectName("panel"); panel.setFixedWidth(220); lay=QVBoxLayout(panel); lay.setContentsMargins(16,20,16,18); lay.setSpacing(4)
        lab=QLabel("ACTION LIBRARY"); lab.setObjectName("eyebrow"); lay.addWidget(lab); self.action_container=QVBoxLayout(); self.action_container.setSpacing(2); lay.addLayout(self.action_container)
        for kind in META: lay.addWidget(self.action_button(kind))
        line=QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet(f"color:{C['line']};"); lay.addSpacing(14); lay.addWidget(line); w=QLabel("WORKSPACE"); w.setObjectName("eyebrow"); lay.addWidget(w); 
        for text,slot in [("⌗  Keyboard map", self.keyboard_map),("⌁  Run history", self.history),("⚙  Preferences", self.preferences)]:
            b=QPushButton(text); b.setObjectName("action"); b.clicked.connect(slot); lay.addWidget(b)
        lay.addStretch(); sig=QLabel("Aplus-Nexus"); sig.setStyleSheet(f"color:{C['violet2']}; font-weight:700;"); lay.addWidget(sig); return panel
    def action_button(self,kind):
        icon,title,desc,color=META[kind]; b=QPushButton(); b.setObjectName("action"); row=QHBoxLayout(b); row.setContentsMargins(0,2,0,2); ico=QLabel(icon); ico.setObjectName("actionIcon"); ico.setStyleSheet(f"color:{color};"); row.addWidget(ico); col=QVBoxLayout(); col.setSpacing(1); t=QLabel(title); t.setObjectName("actionTitle"); d=QLabel(desc); d.setObjectName("actionDesc"); col.addWidget(t); col.addWidget(d); row.addLayout(col); b.clicked.connect(lambda checked=False,k=kind:self.add_step(k)); return b
    def center(self):
        panel=QWidget(); lay=QVBoxLayout(panel); lay.setContentsMargins(0,0,0,0); lay.setSpacing(12); head=QHBoxLayout(); self.file_title=QLabel("Submit form repeatedly"); self.file_title.setObjectName("pageTitle"); head.addWidget(self.file_title); draft=QLabel("/ draft"); draft.setProperty("muted",True); head.addWidget(draft); head.addStretch(); stop=QLabel("Ctrl + Alt + 5 stops the run"); stop.setProperty("muted",True); head.addWidget(stop); lay.addLayout(head)
        card=QFrame(); card.setObjectName("workflowCard"); cardlay=QVBoxLayout(card); cardlay.setContentsMargins(0,0,0,0); cardlay.setSpacing(0); bar=QHBoxLayout(); bar.setContentsMargins(20,16,20,16); bar.setSpacing(8); title=QLabel("Workflow"); title.setStyleSheet("font-weight:700; font-size:15px;"); bar.addWidget(title); self.step_count=QLabel(); self.step_count.setProperty("muted",True); bar.addWidget(self.step_count); bar.addStretch(); add=self.button("+ Add step",lambda:self.add_step("delay")); bar.addWidget(add); cardlay.addLayout(bar); line=QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet(f"color:{C['line']};"); cardlay.addWidget(line)
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True); inner=QWidget(); self.steps_layout=QVBoxLayout(inner); self.steps_layout.setContentsMargins(20,10,20,20); self.steps_layout.setSpacing(8); self.steps_layout.addStretch(); self.scroll.setWidget(inner); cardlay.addWidget(self.scroll,1); lay.addWidget(card,1); return panel
    def inspector(self):
        self.inspector_panel=QFrame(); self.inspector_panel.setObjectName("panel"); self.inspector_panel.setFixedWidth(350); self.inspector_layout=QVBoxLayout(self.inspector_panel); self.inspector_layout.setContentsMargins(24,20,24,18); self.inspector_layout.setSpacing(8); return self.inspector_panel
    def current(self): return self.workflow["steps"][self.selected] if self.workflow["steps"] else {}
    def render_steps(self):
        while self.steps_layout.count()>1:
            item=self.steps_layout.takeAt(0); w=item.widget(); w.deleteLater() if w else None
        steps=self.workflow["steps"]; self.step_count.setText(f"{len(steps)} steps")
        for i,d in enumerate(steps):
            row=StepRow(i,d,i==self.selected); row.clicked.connect(self.step_event); self.steps_layout.insertWidget(i,row)
    def step_event(self, event):
        action, index, *rest = event
        if action == "select": self.selected = index
        elif action == "move": self.move_step(index, rest[0])
        elif action == "delete": self.delete_step(index)
        self.render_steps(); self.render_inspector()
    def render_inspector(self):
        while self.inspector_layout.count():
            item=self.inspector_layout.takeAt(0); w=item.widget(); w.deleteLater() if w else None
        d=self.current(); k=d.get("type","delay")
        eye=QLabel("INSPECTOR"); eye.setObjectName("eyebrow"); self.inspector_layout.addWidget(eye); self.field_label("Step name"); name=QLineEdit(str(d.get("label",META.get(k,("",k,"",C['cyan']))[1]))); name.editingFinished.connect(lambda e,name=name:self.update_value("label",name.text())); self.inspector_layout.addWidget(name); self.field_label("Action"); action=QLabel(META.get(k,("",k,"",C['cyan']))[1]); action.setStyleSheet(f"color:{C['cyan']}; font-size:18px; font-weight:700;"); self.inspector_layout.addWidget(action); self.inspector_layout.addSpacing(12)
        fields={"loop":[("Stop shortcut","stop_hotkey","Ctrl + Alt + 5"),("Iterations (optional)","max_iterations","")],"delay":[("Seconds","seconds","2")],"type":[("Text to type","text","AAAA")],"move":[("X position","x","640"),("Y position","y","420"),("OCR target (optional)","ocr_text","")],"click":[("Button","button","left"),("Clicks","clicks","1"),("Interval","interval","0.08")],"hotkey":[("Keys","keys_text","Ctrl + Enter")],"script":[("Python","script","# available: pyautogui, time")]} .get(k,[])
        for label,key,default in fields:
            self.field_label(label); edit=QLineEdit(str(d.get(key,default))); edit.editingFinished.connect(lambda e,key=key,edit=edit:self.update_value(key,edit.text())); self.inspector_layout.addWidget(edit)
        if k=="move":
            b=self.button("Use current cursor position",self.capture_pointer); self.inspector_layout.addWidget(b)
            check=QCheckBox("Try OCR before coordinates"); check.setChecked(bool(d.get("ocr",True))); check.toggled.connect(lambda v:self.update_value("ocr",v)); self.inspector_layout.addWidget(check)
        if k=="type":
            check=QCheckBox("Use clipboard paste"); check.setChecked(bool(d.get("paste",True))); check.toggled.connect(lambda v:self.update_value("paste",v)); self.inspector_layout.addWidget(check)
        line=QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet(f"color:{C['line']};"); self.inspector_layout.addSpacing(18); self.inspector_layout.addWidget(line); self.field_label("RUN SAFETY"); safe=QLabel("Ctrl + Alt + 5 always stops the active run. Preview never touches your cursor."); safe.setWordWrap(True); safe.setProperty("muted",True); self.inspector_layout.addWidget(safe); self.inspector_layout.addStretch()
    def field_label(self,text):
        l=QLabel(text); l.setObjectName("eyebrow"); l.setStyleSheet(f"font-size:11px; letter-spacing:0; color:{C['muted']};"); self.inspector_layout.addWidget(l)
    def update_value(self,key,value):
        d=self.current();
        if key in {"seconds","x","y","clicks","interval"}:
            try: value=float(value) if "." in str(value) else int(value)
            except ValueError: pass
        if key=="keys_text": d["keys"]=[x.strip() for x in str(value).replace("+",",").split(",") if x.strip()]
        d[key]=value; self.render_steps()
    def add_step(self,kind):
        defaults={"loop":{"type":"loop","label":"Loop until stopped","stop_hotkey":"Ctrl + Alt + 5"},"delay":{"type":"delay","label":"Wait a little","seconds":2},"type":{"type":"type","label":"Type text","text":"AAAA","paste":True},"move":{"type":"move","label":"Move cursor","x":640,"y":420,"ocr":True,"ocr_text":""},"click":{"type":"click","label":"Click mouse","button":"left","clicks":1,"interval":0.08},"hotkey":{"type":"hotkey","label":"Press shortcut","keys":["Ctrl","Enter"],"keys_text":"Ctrl + Enter"},"script":{"type":"script","label":"Run Python snippet","script":"# available: pyautogui, time\n"}}; self.workflow["steps"].append(defaults[kind]); self.selected=len(self.workflow["steps"])-1; self.render_steps(); self.render_inspector(); self.statusBar().showMessage(f"Added {META[kind][1]}")
    def move_step(self,i,delta):
        a=self.workflow["steps"]; n=i+delta
        if 0<=n<len(a): a[i],a[n]=a[n],a[i]; self.selected=n
    def delete_step(self,i):
        a=self.workflow["steps"]
        if len(a)>1: a.pop(i); self.selected=max(0,min(i,len(a)-1))
    def save(self):
        path,_=QFileDialog.getSaveFileName(self,"Save workflow","", "KeyPro workflow (*.kpflow);;JSON (*.json)")
        if path:
            Path(path).write_text(json.dumps(self.workflow,indent=2,ensure_ascii=False),encoding="utf-8")
            self.statusBar().showMessage(f"Saved {Path(path).name}")
    def open(self):
        path,_=QFileDialog.getOpenFileName(self,"Open workflow","", "KeyPro workflow (*.kpflow);;JSON (*.json)")
        if path:
            data=json.loads(Path(path).read_text(encoding="utf-8")); name=data.get("name",Path(path).stem); self.workflows[name]=data; self.switch_workflow(name); self.statusBar().showMessage(f"Opened {Path(path).name}")
    def run(self,preview=False):
        if self.runner and self.runner.is_running(): self.runner.stop(); return
        self.runner=WorkflowRunner(self.workflow,preview=preview,event_queue=self.events); self.runtime_label.setText("Preview" if preview else "Live"); self.statusBar().showMessage("Previewing workflow…" if preview else "Running workflow…"); self.progress.setValue(0); self.runner.start()
    def drain_events(self):
        try:
            while True:
                ev,p=self.events.get_nowait()
                if ev=="progress": self.progress.setValue(int(p))
                elif ev=="log": self.statusBar().showMessage(str(p))
                elif ev=="done": self.statusBar().showMessage("Workflow completed"); self.runtime_label.setText("Idle"); self.progress.setValue(100)
                elif ev=="stopped": self.statusBar().showMessage("Workflow stopped"); self.runtime_label.setText("Idle")
                elif ev=="error": self.statusBar().showMessage(f"Error: {p}"); self.runtime_label.setText("Needs attention")
        except queue.Empty: pass
    def capture_pointer(self):
        try:
            import pyautogui; x,y=pyautogui.position(); self.current().update(x=int(x),y=int(y)); self.render_steps(); self.render_inspector(); self.statusBar().showMessage(f"Captured cursor at {x}, {y}")
        except Exception: self.statusBar().showMessage("Install pyautogui to capture cursor position")
    def keyboard_map(self): QMessageBox.information(self,"Keyboard map","Ctrl + Alt + 5\nStops the active workflow immediately.")
    def history(self): QMessageBox.information(self,"Run history","Run history will appear after the first saved run.")
    def preferences(self): QMessageBox.information(self,"Preferences","Preview mode is safe by default.")
    def closeEvent(self,event):
        if self.runner: self.runner.stop()
        event.accept()

def main():
    app=QApplication(sys.argv); app.setStyle("Fusion"); app.setApplicationName("KeyPro"); app.setWindowIcon(QIcon(icon_pixmap())); win=KeyProWindow(); win.show(); sys.exit(app.exec())
