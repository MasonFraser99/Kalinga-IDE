import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import sys
import io
import time
import threading

class KalingaIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("Kalinga IDE")
        self.root.geometry("1000x700")
        
        self.filename = None
        self.theme = "light"
        self.output_console = None
        self.editor_frame = None
        self.auto_save_thread = None

        self.create_widgets()
        self.create_menu()
        self.auto_save_enabled = True
        self.last_saved_time = time.time()
        self.auto_save_interval = 300  # 5 minutes

    def create_widgets(self):
        # Frame for the editor and output
        self.editor_frame = tk.Frame(self.root)
        self.editor_frame.pack(fill=tk.BOTH, expand=True)

        # Text widget with line numbers
        self.text = tk.Text(self.editor_frame, wrap=tk.WORD, font=("Courier", 12), undo=True, insertbackground='black')
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text.bind("<KeyRelease>", self.highlight_syntax)
        self.text.bind("<KeyRelease>", self.update_line_and_word_count)

        # Scrollbar for the text widget
        self.scrollbar = tk.Scrollbar(self.editor_frame, command=self.text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.config(yscrollcommand=self.scrollbar.set)

        # Line number display
        self.line_number_canvas = tk.Canvas(self.editor_frame, width=40, bg="#f0f0f0", bd=0, highlightthickness=0)
        self.line_number_canvas.pack(side=tk.LEFT, fill=tk.Y)
        self.update_line_numbers()

        # Output console at the bottom
        self.output_console = tk.Text(self.root, height=10, wrap=tk.WORD, font=("Courier", 10), state=tk.DISABLED, bg="#f5f5f5")
        self.output_console.pack(fill=tk.X, side=tk.BOTTOM)

        # Line & Word Count display
        self.status_bar = tk.Label(self.root, text="Lines: 0 | Words: 0", bd=1, relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        # File menu
        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_file)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_command(label="Save As", command=self.save_as_file)
        file_menu.add_command(label="Close", command=self.close_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.close_ide)

        # Run menu
        run_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Run", menu=run_menu)
        run_menu.add_command(label="Run Code", command=self.run_code)
        run_menu.add_separator()
        run_menu.add_command(label="Clear Console", command=self.clear_console)

        # Edit menu
        edit_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo)
        edit_menu.add_command(label="Redo", command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Find", command=self.find_text)
        edit_menu.add_command(label="Replace", command=self.replace_text)
        edit_menu.add_command(label="Auto-format", command=self.auto_format_code)

        # View menu
        view_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Toggle Theme", command=self.toggle_theme)

        # Tools menu
        tools_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Enable Auto-save", command=self.toggle_auto_save)

    def apply_theme(self):
        """Apply selected theme (light or dark)."""
        if self.theme == "light":
            self.text.config(bg="#FFFFFF", fg="black", insertbackground="black")
            self.output_console.config(bg="#f5f5f5", fg="black")
            self.line_number_canvas.config(bg="#f0f0f0")
        elif self.theme == "dark":
            self.text.config(bg="#2e2e2e", fg="white", insertbackground="white")
            self.output_console.config(bg="#333333", fg="white")
            self.line_number_canvas.config(bg="#444444")

    def update_line_and_word_count(self, event=None):
        """Update line and word count in the status bar."""
        line_count = int(self.text.index('end-1c').split('.')[0])
        word_count = len(self.text.get(1.0, tk.END).split())
        self.status_bar.config(text=f"Lines: {line_count} | Words: {word_count}")
        self.update_line_numbers()

    def update_line_numbers(self):
        """Update line numbers."""
        line_count = int(self.text.index('end-1c').split('.')[0])
        self.line_number_canvas.delete("all")
        for i in range(1, line_count + 1):
            self.line_number_canvas.create_text(20, (i * 20), anchor="nw", text=str(i), font=("Courier", 10), fill="#888888")

    def highlight_syntax(self, event=None):
        """Highlight Python syntax (keywords, strings, comments)."""
        self.text.tag_remove("keyword", "1.0", tk.END)
        self.text.tag_remove("string", "1.0", tk.END)
        self.text.tag_remove("comment", "1.0", tk.END)

        keywords = r'\b(def|class|if|else|elif|for|while|return|import|from|try|except|finally|with|as|and|or|not|is|in)\b'
        strings = r'".*?"|\'.*?\''
        comments = r'#.*?$'

        self.apply_syntax_highlight(keywords, "keyword")
        self.apply_syntax_highlight(strings, "string")
        self.apply_syntax_highlight(comments, "comment")

    def apply_syntax_highlight(self, pattern, tag):
        """Apply syntax highlighting for the given pattern and tag."""
        start_idx = "1.0"
        while True:
            start_idx = self.text.search(pattern, start_idx, stopindex=tk.END, regexp=True)
            if not start_idx:
                break
            end_idx = f"{start_idx}+{len(self.text.get(start_idx, start_idx + '+100c'))}c"
            self.text.tag_add(tag, start_idx, end_idx)
            self.text.tag_configure(tag, foreground="blue" if tag == "keyword" else "green" if tag == "string" else "gray")
            start_idx = end_idx

    def new_file(self):
        """Create a new file."""
        if self.filename and self.text.get(1.0, tk.END).strip() != "":
            answer = messagebox.askyesno("Unsaved changes", "Do you want to save changes?")
            if answer:
                self.save_file()
        self.text.delete(1.0, tk.END)
        self.filename = None
        self.update_line_and_word_count()

    def open_file(self):
        """Open an existing file."""
        file = filedialog.askopenfilename(defaultextension=".py", filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if file:
            with open(file, "r", encoding="utf-8") as f:
                content = f.read()
            self.text.delete(1.0, tk.END)
            self.text.insert(tk.END, content)
            self.filename = file
            self.update_line_and_word_count()
            self.root.title(f"Kalinga IDE - {os.path.basename(file)}")  # Update title to reflect file name

    def save_file(self):
        """Save the current file."""
        if self.filename:
            content = self.text.get(1.0, tk.END)
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(content)
            self.last_saved_time = time.time()
        else:
            self.save_as_file()

    def save_as_file(self):
        """Save the current file as a new file."""
        file = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if file:
            content = self.text.get(1.0, tk.END)
            with open(file, "w", encoding="utf-8") as f:
                f.write(content)
            self.filename = file
            self.root.title(f"Kalinga IDE - {os.path.basename(file)}")  # Update title to reflect file name
            self.last_saved_time = time.time()

    def close_file(self):
        """Close the current file."""
        self.text.delete(1.0, tk.END)
        self.filename = None
        self.update_line_and_word_count()

    def close_ide(self):
        """Close the IDE."""
        if self.filename and self.text.get(1.0, tk.END).strip() != "":
            answer = messagebox.askyesno("Unsaved changes", "You have unsaved changes. Do you want to save them before quitting?")
            if answer:
                self.save_file()
        self.root.quit()

    def run_code(self):
        """Run the code from the editor."""
        code = self.text.get(1.0, tk.END)
        if not code.strip():
            messagebox.showwarning("Empty Code", "There is no code to run.")
            return

        self.clear_console()
        self.output_console.config(state=tk.NORMAL)
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            exec(code, globals())
            output = sys.stdout.getvalue()
            self.output_console.insert(tk.END, output)
        except Exception as e:
            self.output_console.insert(tk.END, f"Error: {e}")
        finally:
            self.output_console.config(state=tk.DISABLED)

    def clear_console(self):
        """Clear the output console."""
        self.output_console.config(state=tk.NORMAL)
        self.output_console.delete(1.0, tk.END)
        self.output_console.config(state=tk.DISABLED)

    def toggle_theme(self):
        """Toggle between light and dark theme."""
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_theme()

    def toggle_auto_save(self):
        """Toggle auto-save functionality."""
        self.auto_save_enabled = not self.auto_save_enabled
        if self.auto_save_enabled:
            self.auto_save_thread = threading.Thread(target=self.auto_save)
            self.auto_save_thread.daemon = True
            self.auto_save_thread.start()

    def auto_save(self):
        """Automatically save the file every few minutes."""
        while self.auto_save_enabled:
            time.sleep(self.auto_save_interval)
            if self.filename:
                current_time = time.time()
                if current_time - self.last_saved_time >= self.auto_save_interval:
                    self.save_file()

    def undo(self):
        """Undo the last action."""
        self.text.edit_undo()

    def redo(self):
        """Redo the last undone action."""
        self.text.edit_redo()

    def auto_format_code(self):
        """Auto-format the Python code."""
        import autopep8
        content = self.text.get(1.0, tk.END)
        formatted_code = autopep8.fix_code(content)
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, formatted_code)

    def find_text(self):
        """Search for text."""
        search_query = simpledialog.askstring("Find", "Enter text to find:")
        if search_query:
            start_idx = "1.0"
            while True:
                start_idx = self.text.search(search_query, start_idx, stopindex=tk.END)
                if not start_idx:
                    break
                end_idx = f"{start_idx}+{len(search_query)}c"
                self.text.tag_add("find", start_idx, end_idx)
                self.text.tag_configure("find", background="yellow")
                start_idx = end_idx

    def replace_text(self):
        """Replace text."""
        find_query = simpledialog.askstring("Find", "Enter text to find:")
        replace_query = simpledialog.askstring("Replace", "Enter text to replace:")
        if find_query and replace_query:
            content = self.text.get(1.0, tk.END)
            new_content = content.replace(find_query, replace_query)
            self.text.delete(1.0, tk.END)
            self.text.insert(tk.END, new_content)

if __name__ == "__main__":
    root = tk.Tk()
    ide = KalingaIDE(root)
    root.mainloop()
