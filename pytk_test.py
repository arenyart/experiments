import tkinter as tk
from tkinter import ttk

def label_clicked():
    print("Label clicked!")

def button_clicked():
    print("Button clicked!")

def entry_changed(event):
    value = entry.get()
    print(f"Entry changed: {value}")

def checkbutton_changed():
    value = checkbutton_var.get()
    print(f"Checkbutton changed: {value}")

def radio_changed():
    value = radio_var.get()
    print(f"Radiobutton changed: {value}")

def combobox_changed(event):
    value = combobox.get()
    print(f"Combobox changed: {value}")

def listbox_selected(event):
    selection = listbox.curselection()
    if selection:
        index = selection[0]
        value = listbox.get(index)
        print(f"Listbox selected: {value}")

def scale_changed(event):
    value = scale.get()
    print(f"Scale changed: {value}")

def spinbox_changed():
    value = spinbox.get()
    print(f"Spinbox changed: {value}")

def notebook_changed(event):
    tab_index = notebook.index(notebook.select())
    print(f"Notebook changed: Tab {tab_index+1}")

def text_changed(event):
    value = text.get("1.0", tk.END).strip()
    print(f"Text changed: {value}")

def treeview_selected(event):
    selection = treeview.selection()
    if selection:
        item = selection[0]
        value = treeview.item(item)["text"]
        print(f"Treeview selected: {value}")

root = tk.Tk()
root.title("Tkinter Widgets Demo")

# Label widget
label = ttk.Label(root, text="Label Widget")
label.pack()
label.bind("<Button-1>", lambda event: label_clicked())

# Button widget
button = ttk.Button(root, text="Button Widget", command=button_clicked)
button.pack()

# Entry widget
entry = ttk.Entry(root)
entry.pack()
entry.bind("<KeyRelease>", entry_changed)

# Checkbutton widget
checkbutton_var = tk.StringVar()
checkbutton = ttk.Checkbutton(root, text="Checkbutton Widget", variable=checkbutton_var, command=checkbutton_changed)
checkbutton.pack()

# Radiobutton widget
radio_var = tk.StringVar()
radiobutton1 = ttk.Radiobutton(root, text="Radio 1", variable=radio_var, value="Radio 1", command=radio_changed)
radiobutton1.pack()

radiobutton2 = ttk.Radiobutton(root, text="Radio 2", variable=radio_var, value="Radio 2", command=radio_changed)
radiobutton2.pack()

# Combobox widget
combobox = ttk.Combobox(root, values=["Option 1", "Option 2", "Option 3"])
combobox.pack()
combobox.bind("<<ComboboxSelected>>", combobox_changed)

# Listbox widget
listbox = tk.Listbox(root)
for i in range(10):
    listbox.insert(tk.END, f"Item {i+1}")
listbox.pack()
listbox.bind("<<ListboxSelect>>", listbox_selected)

# Scale widget
scale = ttk.Scale(root, from_=0, to=100)
scale.pack()
scale.bind("<ButtonRelease-1>", scale_changed)

# Spinbox widget
spinbox = ttk.Spinbox(root, from_=0, to=10, command=spinbox_changed)
spinbox.pack()

# Notebook widget
notebook = ttk.Notebook(root)
tab1 = ttk.Frame(notebook)
tab2 = ttk.Frame(notebook)
notebook.add(tab1, text="Tab 1")
notebook.add(tab2, text="Tab 2")
notebook.pack()
notebook.bind("<<NotebookTabChanged>>", notebook_changed)

# Text widget
text = tk.Text(tab1, height=10, width=40)
text.pack()
text.bind("<KeyRelease>", text_changed)

# Text widget
text2 = tk.Text(tab2, height=10, width=40)
text2.pack()
text2.bind("<KeyRelease>", text_changed)

# Treeview widget
treeview = ttk.Treeview(root)
treeview.heading("#0", text="Treeview Widget")
treeview.insert("", tk.END, text="Item 1")
treeview.insert("", tk.END, text="Item 2")
treeview.pack()
treeview.bind("<<TreeviewSelect>>", treeview_selected)

root.mainloop()
