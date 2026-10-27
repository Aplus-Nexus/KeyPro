"""Portable workflow model and optional input runtime for KeyPressor."""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

try:
    import pyautogui
except Exception:
    pyautogui = None
try:
    from pynput import keyboard
except Exception:
    keyboard = None
try:
    import pytesseract
except Exception:
    pytesseract = None
try:
    import pyperclip
except Exception:
    pyperclip = None

DEFAULT_WORKFLOW = [
    {"type":"loop","label":"Loop until stopped","stop_hotkey":"Ctrl + Alt + 5","max_iterations":""},
    {"type":"delay","label":"Wait 2 seconds","seconds":2},
    {"type":"type","label":"Type text","text":"AAAA","paste":True},
    {"type":"move","label":"Move cursor","x":640,"y":420,"ocr":True,"ocr_text":""},
    {"type":"click","label":"Click mouse","button":"left","clicks":1,"interval":0.08},
    {"type":"hotkey","label":"Press shortcut","keys":["Ctrl","Enter"],"keys_text":"Ctrl + Enter"},
]

@dataclass
class Step:
    type: str
    label: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self):
        out = dict(self.params); out.update(type=self.type, label=self.label or self.type.title()); return out
    @classmethod
    def from_dict(cls, data):
        d = dict(data); kind=d.pop("type", "delay"); label=d.pop("label", kind.title()); return cls(kind,label,d)

class Workflow:
    def __init__(self,name="Untitled workflow",steps=None): self.name=name; self.steps=steps or []
    @classmethod
    def from_dict(cls,data): return cls(data.get("name","Untitled workflow"),[Step.from_dict(s) for s in data.get("steps",[])])
    def to_dict(self): return {"name":self.name,"version":1,"steps":[s.to_dict() for s in self.steps]}

class WorkflowRunner(threading.Thread):
    """Run a workflow off the UI thread. Preview emits logs without input side effects."""
    daemon = True
    def __init__(self,workflow,preview=False,event_queue=None):
        super().__init__(); self.workflow=Workflow.from_dict(workflow) if isinstance(workflow,dict) else workflow; self.preview=preview; self.events=event_queue or queue.Queue(); self.stop_event=threading.Event(); self._listener=None; self._running=False
    def is_running(self): return self._running and self.is_alive()
    def stop(self): self.stop_event.set(); self._stop_listener()
    def emit(self,event,payload=None): self.events.put((event,payload))
    def run(self):
        self._running=True
        try:
            steps=self.workflow.steps; loop_index=next((i for i,s in enumerate(steps) if s.type=="loop"),None)
            self._start_listener("Ctrl + Alt + 5" if loop_index is None else self.workflow.steps[loop_index].params.get("stop_hotkey","Ctrl + Alt + 5"))
            if loop_index is None: self._run_steps(steps)
            else:
                prefix=steps[:loop_index]; body=steps[loop_index+1:]; loop=steps[loop_index]; iterations=0; max_iter=str(loop.params.get("max_iterations","")).strip()
                if prefix: self._run_steps(prefix)
                while not self.stop_event.is_set():
                    iterations+=1; self._run_steps(body,iterations)
                    if max_iter and iterations>=int(max_iter): break
                    if not body: break
            if self.stop_event.is_set(): self.emit("stopped")
            else: self.emit("done")
        except Exception as exc: self.emit("error",str(exc))
        finally: self._stop_listener(); self._running=False
    def _run_steps(self,steps,iteration=1):
        total=max(1,len(steps))
        for idx,step in enumerate(steps):
            if self.stop_event.is_set(): return
            self.emit("progress", round(idx/total*100)); self.emit("log", f"{step.label or step.type.title()} · {'preview' if self.preview else 'running'}")
            self._run_step(step)
        self.emit("progress",100)
    def _run_step(self,step):
        p=step.params; kind=step.type
        if kind=="delay": self._sleep(float(p.get("seconds",2))); return
        if self.preview:
            self._sleep(0.14); return
        if kind=="type":
            text=str(p.get("text",""));
            if pyautogui:
                # Clipboard paste keeps non-ASCII text intact; write is the portable fallback.
                if p.get("paste", True) and pyperclip and any(ord(ch)>127 for ch in text):
                    pyperclip.copy(text); pyautogui.hotkey("ctrl","v")
                else: pyautogui.write(text,interval=0.02)
        elif kind=="move":
            x,y=int(float(p.get("x",640))),int(float(p.get("y",420)))
            target = str(p.get("ocr_text", "")).strip()
            match = self._ocr_target(target) if p.get("ocr", True) and target else None
            if match: x,y = match
            if pyautogui: pyautogui.moveTo(x,y,duration=0.2)
        elif kind=="click":
            if pyautogui: pyautogui.click(button=p.get("button","left"),clicks=int(p.get("clicks",1)),interval=float(p.get("interval",0.08)))
        elif kind=="hotkey":
            keys=p.get("keys") or [x.strip() for x in str(p.get("keys_text","Ctrl + Enter")).split("+")]
            if pyautogui: pyautogui.hotkey(*[self._key(k) for k in keys])
        elif kind=="script":
            scope={"time":time,"pyautogui":pyautogui,"stop_event":self.stop_event}; exec(str(p.get("script","")),scope,scope)
    def _sleep(self,seconds):
        end=time.monotonic()+max(0,seconds)
        while time.monotonic()<end and not self.stop_event.is_set(): self.stop_event.wait(min(0.08,end-time.monotonic()))
    def _key(self,k): return {"Ctrl":"ctrl","Control":"ctrl","Alt":"alt","Shift":"shift","Enter":"enter","Cmd":"command","Command":"command","Space":"space"}.get(k,k.lower())
    def _ocr_target(self, target):
        """Best-effort text lookup. Returning None preserves coordinate fallback."""
        if not (pyautogui and pytesseract): return None
        try:
            image = pyautogui.screenshot()
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            needle = target.casefold()
            for i, raw in enumerate(data.get("text", [])):
                if needle in str(raw).casefold():
                    left, top = int(data["left"][i]), int(data["top"][i]); width, height = int(data["width"][i]), int(data["height"][i])
                    return left + width // 2, top + height // 2
        except Exception:
            return None
        return None
    def _start_listener(self,hotkey):
        if keyboard is None:return
        wanted={self._key(k.strip()) for k in hotkey.replace("+",",").split(",") if k.strip()}; pressed=set()
        def on_press(key):
            try:name=key.char.lower() if getattr(key,"char",None) else str(key).split(".")[-1].lower()
            except Exception:name=str(key).lower()
            pressed.add(name)
            if any(x in pressed for x in wanted if x in {"ctrl","alt","shift","command"}) and any(x in pressed for x in wanted if x not in {"ctrl","alt","shift","command"}): self.stop_event.set()
        def on_release(key):
            try:name=key.char.lower() if getattr(key,"char",None) else str(key).split(".")[-1].lower()
            except Exception:name=str(key).lower()
            pressed.discard(name)
        try:self._listener=keyboard.Listener(on_press=on_press,on_release=on_release); self._listener.daemon=True; self._listener.start()
        except Exception:self._listener=None
    def _stop_listener(self):
        if self._listener:
            try:self._listener.stop()
            except Exception:pass
            self._listener=None
