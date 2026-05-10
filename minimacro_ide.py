import tkinter as tk
from tkinter import ttk, scrolledtext
import re

class MacroProcessor:
    def __init__(self):
        self.MNT = [] # List of dicts: {'name': name, 'mdt_index': index, 'num_params': num}
        self.MDT = [] # List of strings (lines)
        self.intermediate_code = []
        self.expanded_code = []
        self.errors = []
        # Language Keywords (5 as per requirement)
        self.keywords = {'MACRO', 'MEND', 'START', 'END', 'PRINT'}
        # Additional standard instructions to avoid false "undefined macro" errors
        self.valid_instructions = {'LOAD', 'STORE', 'ADD', 'SUB', 'MOV'}

    def pass_1(self, source_lines):
        self.MNT = []
        self.MDT = []
        self.intermediate_code = []
        self.errors = []
        
        in_macro = False
        macro_name = None
        params_map = {} # Maps formal param name to positional index like '#1'
        
        i = 0
        while i < len(source_lines):
            line = source_lines[i].strip()
            if not line or line.startswith(';'): # Skip empty lines and comments in Pass 1 for intermediate
                self.intermediate_code.append((i+1, line)) # Keep comments for context
                i += 1
                continue
                
            parts = re.split(r'[ \t,]+', line)
            parts = [p for p in parts if p]
            
            if not parts:
                i += 1
                continue
                
            if parts[0] == 'MACRO':
                if in_macro:
                    self.errors.append(f"Line {i+1}: Error - Nested MACRO definition not allowed.")
                in_macro = True
                # Next line must be the macro header
                i += 1
                if i >= len(source_lines):
                    self.errors.append("Error - Unexpected end of file during MACRO definition.")
                    break
                header_line = source_lines[i].strip()
                header_parts = re.split(r'[ \t,]+', header_line)
                header_parts = [p for p in header_parts if p]
                
                if not header_parts:
                    self.errors.append(f"Line {i+1}: Error - Invalid macro header.")
                    in_macro = False
                    i += 1
                    continue
                    
                macro_name = header_parts[0]
                formal_params = header_parts[1:]
                
                self.MNT.append({
                    'name': macro_name,
                    'mdt_index': len(self.MDT),
                    'num_params': len(formal_params)
                })
                
                params_map = {param: f"#{idx+1}" for idx, param in enumerate(formal_params)}
                
            elif parts[0] == 'MEND':
                if not in_macro:
                    self.errors.append(f"Line {i+1}: Error - MEND without starting MACRO.")
                else:
                    self.MDT.append('MEND')
                    in_macro = False
                    params_map = {}
            else:
                if in_macro:
                    # Substitute formal parameters
                    processed_line = line
                    # Need to replace whole words only to avoid partial matches
                    for param, pos in params_map.items():
                        processed_line = re.sub(rf'\b{param}\b', pos, processed_line)
                    self.MDT.append(processed_line)
                else:
                    self.intermediate_code.append((i+1, line))
            
            i += 1
            
        if in_macro:
            self.errors.append("Error - Missing MEND for a MACRO definition.")

    def pass_2(self):
        self.expanded_code = []
        mnt_dict = {entry['name']: entry for entry in self.MNT}
        
        for original_line_num, line in self.intermediate_code:
            if not line or line.startswith(';'):
                self.expanded_code.append(line)
                continue

            parts = re.split(r'[ \t,]+', line)
            parts = [p for p in parts if p]
            
            if not parts:
                continue
                
            opcode = parts[0]
            
            if opcode in mnt_dict:
                # Macro invocation
                mnt_entry = mnt_dict[opcode]
                actual_params = parts[1:]
                
                if len(actual_params) != mnt_entry['num_params']:
                    self.errors.append(f"Line {original_line_num}: Error - Incorrect parameters for macro '{opcode}'. Expected {mnt_entry['num_params']}, got {len(actual_params)}.")
                    self.expanded_code.append(f"; ERROR: Macro '{opcode}' expansion failed (Argument mismatch)")
                    continue
                    
                # Expand Macro
                self.expanded_code.append(f"; -- Expanding Macro: {opcode} --")
                mdt_idx = mnt_entry['mdt_index']
                while mdt_idx < len(self.MDT) and self.MDT[mdt_idx] != 'MEND':
                    mdt_line = self.MDT[mdt_idx]
                    expanded_line = mdt_line
                    # Substitute #n with actual parameters
                    for idx, act_param in enumerate(actual_params):
                        expanded_line = expanded_line.replace(f"#{idx+1}", act_param)
                    self.expanded_code.append(expanded_line)
                    mdt_idx += 1
                self.expanded_code.append(f"; -- End Expansion: {opcode} --")
            else:
                # Normal statement
                self.expanded_code.append(line)
                
                # Semantic Check for undefined macros
                if opcode not in self.keywords and opcode not in self.valid_instructions:
                    self.errors.append(f"Line {original_line_num}: Error - Undefined macro or command '{opcode}'.")

    def process(self, source_code):
        lines = source_code.split('\n')
        self.pass_1(lines)
        self.pass_2()
        return {
            'mnt': self.MNT,
            'mdt': self.MDT,
            'expanded': '\n'.join(self.expanded_code),
            'errors': self.errors
        }


class MiniMacroIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("MiniMacro Processor IDE")
        self.root.geometry("1100x700")
        
        # Style configurations
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=5)
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        
        self.processor = MacroProcessor()
        
        self.setup_ui()
        self.load_sample_code()
        
    def setup_ui(self):
        # Create PanedWindow for left (code) and right (tables/output)
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # --- Left Frame: Input Code ---
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Source Code (MiniMacro):", font=('Segoe UI', 11, 'bold')).pack(anchor=tk.W)
        self.input_text = scrolledtext.ScrolledText(left_frame, width=45, height=30, font=('Consolas', 11))
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        run_btn = ttk.Button(left_frame, text="▶ Run Macro Processor", command=self.run_processor)
        run_btn.pack(fill=tk.X, pady=5)
        
        # --- Right Frame: Outputs ---
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        # Output notebook
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Expanded Code
        self.tab_expanded = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_expanded, text="Expanded Output Code")
        self.expanded_text = scrolledtext.ScrolledText(self.tab_expanded, font=('Consolas', 11), bg='#F8F9FA')
        self.expanded_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 2: Tables (MNT & MDT)
        self.tab_tables = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tables, text="Internal Tables (MNT & MDT)")
        
        # MNT Table
        ttk.Label(self.tab_tables, text="Macro Name Table (MNT):", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, padx=5, pady=5)
        self.mnt_tree = ttk.Treeview(self.tab_tables, columns=("Index", "Name", "MDT_Index", "Num_Params"), show="headings", height=4)
        self.mnt_tree.heading("Index", text="Index")
        self.mnt_tree.heading("Name", text="Macro Name")
        self.mnt_tree.heading("MDT_Index", text="MDT Index")
        self.mnt_tree.heading("Num_Params", text="Parameters")
        self.mnt_tree.column("Index", width=50, anchor=tk.CENTER)
        self.mnt_tree.column("Name", anchor=tk.CENTER)
        self.mnt_tree.column("MDT_Index", width=100, anchor=tk.CENTER)
        self.mnt_tree.column("Num_Params", width=100, anchor=tk.CENTER)
        self.mnt_tree.pack(fill=tk.X, padx=5)
        
        # MDT Table
        ttk.Label(self.tab_tables, text="Macro Definition Table (MDT):", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, padx=5, pady=5)
        self.mdt_tree = ttk.Treeview(self.tab_tables, columns=("Index", "Instruction"), show="headings")
        self.mdt_tree.heading("Index", text="Index")
        self.mdt_tree.heading("Instruction", text="Instruction Body")
        self.mdt_tree.column("Index", width=50, anchor=tk.CENTER)
        self.mdt_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # --- Errors Section at bottom of right frame ---
        ttk.Label(right_frame, text="Error Detection & Console Log:", font=('Segoe UI', 10, 'bold'), foreground="#D32F2F").pack(anchor=tk.W, pady=(10, 0))
        self.error_text = scrolledtext.ScrolledText(right_frame, height=6, font=('Consolas', 10), foreground="#D32F2F", bg='#FFEBEE')
        self.error_text.pack(fill=tk.X, pady=5)

    def load_sample_code(self):
        sample = """; MiniMacro Sample Program
; Language Keywords: MACRO, MEND, START, END, PRINT
; -----------------------------------

; Definition 1: Two parameters
MACRO
ADD_VARS X, Y
LOAD X
ADD Y
STORE X
MEND

; Definition 2: One parameter
MACRO
DISPLAY VAL
PRINT VAL
MEND

START

; 1. Valid Macro Calls
ADD_VARS NUM1, NUM2
DISPLAY RESULT

; 2. Error Demonstration: Incorrect parameter count
; Expects 2 parameters, sending 3
ADD_VARS A, B, C

; 3. Error Demonstration: Undefined macro
UNKNOWN_CMD DATA

END
"""
        self.input_text.insert(tk.END, sample)
        
    def run_processor(self):
        # Get source code
        source = self.input_text.get("1.0", tk.END)
        
        # Run backend logic
        result = self.processor.process(source)
        
        # Display Expanded Code
        self.expanded_text.delete("1.0", tk.END)
        self.expanded_text.insert(tk.END, result['expanded'])
        
        # Display MNT
        for item in self.mnt_tree.get_children():
            self.mnt_tree.delete(item)
        for i, entry in enumerate(result['mnt']):
            self.mnt_tree.insert("", "end", values=(i, entry['name'], entry['mdt_index'], entry['num_params']))
            
        # Display MDT
        for item in self.mdt_tree.get_children():
            self.mdt_tree.delete(item)
        for i, line in enumerate(result['mdt']):
            self.mdt_tree.insert("", "end", values=(i, line))
            
        # Display Errors
        self.error_text.delete("1.0", tk.END)
        if result['errors']:
            self.error_text.insert(tk.END, "\\n".join(result['errors']))
        else:
            self.error_text.configure(foreground="green")
            self.error_text.insert(tk.END, "✓ Compilation finished successfully with 0 errors.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MiniMacroIDE(root)
    root.mainloop()
