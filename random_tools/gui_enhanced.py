"""基于 ttkbootstrap 的抽奖工具，支持从 JSON 数据随机选人。"""

from __future__ import annotations

import json
import random
from datetime import datetime
from pathlib import Path
import tkinter as tk
from ttkbootstrap import Style
from ttkbootstrap import ttk  # 使用 ttkbootstrap 的 ttk 小部件
from ttkbootstrap.constants import PRIMARY
from ttkbootstrap.dialogs import Messagebox
import sys
import shutil


APP_NAME = "LuckyDraw"

# 兼容 PyInstaller 打包后的资源定位
# 当被 PyInstaller 冻结时，sys._MEIPASS 指向临时解包目录的根
# 我们将 participants.json 放在应用根目录（见打包脚本中的 --add-data 配置）
# 同时在冻结态时，把数据文件复制到用户可写目录（~/.luckydraw）供读写

def _resource_path(name: str) -> Path:
	try:
		base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
	except Exception:
		base = Path(__file__).parent
	return base / name


def _data_file_path() -> Path:
	res_file = _resource_path("participants.json")
	# 非冻结态：直接读写项目内文件，便于开发
	if not getattr(sys, "frozen", False):
		return res_file
	# 冻结态：使用用户家目录下的可写文件
	user_dir = Path.home() / ".luckydraw"
	user_dir.mkdir(parents=True, exist_ok=True)
	user_file = user_dir / "participants.json"
	if not user_file.exists():
		try:
			if res_file.exists():
				shutil.copy2(res_file, user_file)
			else:
				user_file.write_text("[]", encoding="utf-8")
		except Exception:
			# 回退写入空数组
			try:
				user_file.write_text("[]", encoding="utf-8")
			except Exception:
				pass
	return user_file


DATA_FILE = _data_file_path()


class LuckyDrawApp:
	"""抽奖工具界面与逻辑封装。"""

	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("阎王点卯")
		self.root.geometry("560x480")
		self.root.resizable(False, False)

		self.names: list[str] = []
		self.draw_count = 0
		self.animation_after_id: str | None = None
		self.final_choice: str | None = None
		self.animation_running = False

		# 仅用于设置主题，不作为控件工厂
		self.style = Style(theme="cosmo")
		self._build_menu()
		self._build_layout()
		self._load_participants()

	def _build_menu(self) -> None:
		menubar = tk.Menu(self.root)
		# 数据菜单
		data_menu = tk.Menu(menubar, tearoff=False)
		data_menu.add_command(label="编辑参与者...", command=self._open_participants_editor, accelerator="Ctrl/Cmd+E")
		menubar.add_cascade(label="数据", menu=data_menu)
		# 文件菜单
		file_menu = tk.Menu(menubar, tearoff=False)
		file_menu.add_command(label="退出", command=self._on_close, accelerator="Ctrl/Cmd+Q")
		menubar.add_cascade(label="文件", menu=file_menu)
		self.root.config(menu=menubar)

		# 绑定快捷键（Windows/Linux 用 Ctrl，macOS 用 Command）
		self.root.bind_all("<Control-e>", lambda e: self._open_participants_editor())
		self.root.bind_all("<Command-e>", lambda e: self._open_participants_editor())
		self.root.bind_all("<Control-q>", lambda e: self._on_close())
		self.root.bind_all("<Command-q>", lambda e: self._on_close())

	def _build_layout(self) -> None:
		container = ttk.Frame(self.root, padding=20)
		container.pack(fill=tk.BOTH, expand=True)

		self.highlight_var = tk.StringVar(value="准备抽奖")
		highlight = ttk.Label(container, textvariable=self.highlight_var, font=("微软雅黑", 26, "bold"), bootstyle="success")
		highlight.pack(pady=(0, 20))

		text_frame = ttk.Frame(container)
		text_frame.pack(fill=tk.BOTH, expand=True)

		self.result_text = tk.Text(
			text_frame,
			height=12,
			wrap="word",
			state=tk.DISABLED,
			font=("微软雅黑", 12),
			background="#ffffff",
			relief=tk.FLAT,
		)
		scrollbar = ttk.Scrollbar(text_frame, command=self.result_text.yview)
		self.result_text.configure(yscrollcommand=scrollbar.set)

		self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

		button_frame = ttk.Frame(container)
		button_frame.pack(pady=20)

		self.draw_button = ttk.Button(button_frame, text="开始抽奖", command=self.start_draw, bootstyle=PRIMARY)
		self.draw_button.grid(row=0, column=0, padx=10)

		self.clear_button = ttk.Button(button_frame, text="清空结果", command=self.clear_results, bootstyle="secondary")
		self.clear_button.grid(row=0, column=1, padx=10)

	def _extract_names(self, obj) -> list[str]:
		"""从加载的 JSON 对象中提取姓名列表。支持字符串或带 name 字段的对象。"""
		names: list[str] = []
		if isinstance(obj, list):
			for item in obj:
				if isinstance(item, str) and item.strip():
					names.append(item.strip())
				elif isinstance(item, dict):
					name = str(item.get("name", "")).strip()
					if name:
						names.append(name)
		return names

	def _load_participants(self) -> None:
		if not DATA_FILE.exists():
			Messagebox.show_error("未找到参与者数据文件：\n" + str(DATA_FILE), title="数据缺失")
			self.draw_button.configure(state=tk.DISABLED)
			return

		try:
			raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
		except json.JSONDecodeError as exc:
			Messagebox.show_error(f"参与者数据文件格式错误：\n{exc}", title="JSON解析失败")
			self.draw_button.configure(state=tk.DISABLED)
			return

		names = self._extract_names(raw)
		if not names:
			Messagebox.show_warning("参与者列表为空，请添加后再试。", title="无参与者")
			self.draw_button.configure(state=tk.DISABLED)
			return

		self.names = names
		self.draw_button.configure(state=tk.NORMAL)
		self.highlight_var.set(f"已加载 {len(self.names)} 位参与者")

	def _open_participants_editor(self) -> None:
		"""打开编辑窗口，直接编辑 participants.json 的数组内容。"""
		editor = tk.Toplevel(self.root)
		editor.title("编辑参与者")
		editor.geometry("640x520")
		editor.transient(self.root)
		editor.grab_set()

		frame = ttk.Frame(editor, padding=10)
		frame.pack(fill=tk.BOTH, expand=True)

		info = ttk.Label(frame, text="请以 JSON 数组格式编辑参与者（支持字符串或包含 name 字段的对象）", bootstyle="secondary")
		info.pack(anchor=tk.W, pady=(0, 6))

		text_frame = ttk.Frame(frame)
		text_frame.pack(fill=tk.BOTH, expand=True)

		text = tk.Text(text_frame, wrap="word", font=("微软雅黑", 12))
		sb = ttk.Scrollbar(text_frame, command=text.yview)
		text.configure(yscrollcommand=sb.set)
		text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		sb.pack(side=tk.RIGHT, fill=tk.Y)

		# 预填充当前文件内容
		default_json = "[]"
		if DATA_FILE.exists():
			try:
				default_json = json.dumps(json.loads(DATA_FILE.read_text(encoding="utf-8")), ensure_ascii=False, indent=2)
			except Exception:
				default_json = DATA_FILE.read_text(encoding="utf-8", errors="ignore")
		text.insert("1.0", default_json)

		btn_bar = ttk.Frame(frame)
		btn_bar.pack(fill=tk.X, pady=10)

		def on_save(event: object | None = None) -> None:
			content = text.get("1.0", tk.END).strip()
			try:
				obj = json.loads(content)
			except json.JSONDecodeError as exc:
				Messagebox.show_error(f"JSON 格式错误：\n{exc}", title="保存失败")
				return
			if not isinstance(obj, list):
				Messagebox.show_warning("顶层必须是 JSON 数组。", title="保存失败")
				return
			names = self._extract_names(obj)
			if not names:
				Messagebox.show_warning("至少需要 1 个有效的参与者（字符串或包含 name）。", title="保存失败")
				return
			# 保存为规范化的 JSON（保留对象结构，中文不转义）
			DATA_FILE.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
			self._load_participants()
			Messagebox.show_info("保存成功，已重新加载参与者列表。", title="已保存")
			editor.destroy()

		def on_cancel(event: object | None = None) -> None:
			editor.destroy()

		save_btn = ttk.Button(btn_bar, text="保存", command=on_save, bootstyle=PRIMARY)
		save_btn.pack(side=tk.RIGHT, padx=6)
		cancel_btn = ttk.Button(btn_bar, text="取消", command=on_cancel, bootstyle="secondary")
		cancel_btn.pack(side=tk.RIGHT)

		# 编辑窗口快捷键
		editor.bind_all("<Control-s>", on_save)
		editor.bind_all("<Command-s>", on_save)
		editor.bind("<Escape>", on_cancel)

	def start_draw(self) -> None:
		if self.animation_running:
			return
		if not self.names:
			Messagebox.show_warning("请先添加参与者。", title="无参与者")
			return

		self.final_choice = random.choice(self.names)
		self.animation_running = True
		self.draw_button.configure(state=tk.DISABLED)
		self.clear_button.configure(state=tk.DISABLED)
		self.highlight_var.set("抽奖中...")
		self._animate_spin(step=0, total_steps=24)

	def _animate_spin(self, step: int, total_steps: int) -> None:
		if step < total_steps:
			preview_name = random.choice(self.names)
			self.highlight_var.set(f"{preview_name}")

			interval = int(40 + (step / total_steps) * 160)
			self.animation_after_id = self.root.after(interval, self._animate_spin, step + 1, total_steps)
		else:
			self.animation_after_id = None
			self._complete_draw()

	def _complete_draw(self) -> None:
		if not self.final_choice:
			return
		winner = self.final_choice
		self.final_choice = None
		self.highlight_var.set(f"倒霉蛋：{winner}")
		self.draw_count += 1
		timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		self._append_result(f"{self.draw_count:02d}. {winner} （{timestamp}）")
		self.animation_running = False
		self.draw_button.configure(state=tk.NORMAL)
		self.clear_button.configure(state=tk.NORMAL)

	def _append_result(self, text: str) -> None:
		self.result_text.configure(state=tk.NORMAL)
		self.result_text.insert(tk.END, text + "\n")
		self.result_text.see(tk.END)
		self.result_text.configure(state=tk.DISABLED)

	def clear_results(self) -> None:
		if self.animation_running:
			return
		self.draw_count = 0
		self.result_text.configure(state=tk.NORMAL)
		self.result_text.delete("1.0", tk.END)
		self.result_text.configure(state=tk.DISABLED)
		self.highlight_var.set("结果已清空")

	def run(self) -> None:
		self.root.protocol("WM_DELETE_WINDOW", self._on_close)
		self.root.mainloop()

	def _on_close(self) -> None:
		if self.animation_after_id is not None:
			self.root.after_cancel(self.animation_after_id)
		self.root.destroy()


def main() -> None:
	root = tk.Tk()
	app = LuckyDrawApp(root)
	app.run()


if __name__ == "__main__":
	main()