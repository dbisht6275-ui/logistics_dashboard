import customtkinter as ctk
from tkcalendar import DateEntry
from reports.HubLorryRate import get_Hub_Lorry_Rate
from ui.treeview import show_treeview
from utils.export_excel import set_report_period

def load_report(content):   # ✅ IMPORTANT CHANGE
    # Clear existing widgets
    for widget in content.winfo_children():
        widget.destroy()

    # Main frame
    frame = ctk.CTkFrame(content, fg_color="transparent")
    frame.pack(pady=20, padx=20, fill="both", expand=True)

    # Title
    ctk.CTkLabel(
        frame, 
        text="📊 Hub Lorry Rate", 
        font=ctk.CTkFont(size=20, weight="bold")
    ).pack(pady=20)

    # -------------------
    # Date Range
    # -------------------
    row_frame = ctk.CTkFrame(frame)
    row_frame.pack(fill="x", pady=12)

    row_frame.grid_columnconfigure(0, weight=1)
    row_frame.grid_columnconfigure(1, weight=0)

    # From
    ctk.CTkLabel(row_frame, text="From").grid(row=0, column=0, padx=20, pady=15, sticky="w")
    from_entry = DateEntry(row_frame, date_pattern="dd-mm-yyyy", width=18)
    from_entry.grid(row=0, column=1, padx=5, pady=15)

    # To
    ctk.CTkLabel(row_frame, text="To").grid(row=0, column=2, padx=20, pady=15, sticky="w")
    to_entry = DateEntry(row_frame, date_pattern="dd-mm-yyyy", width=18)
    to_entry.grid(row=0, column=3, padx=5, pady=15)

    # Generate
    def generate():
        try:
            from_date = from_entry.get()
            to_date   = to_entry.get()

            set_report_period(from_date, to_date)

            columns, rows = get_Hub_Lorry_Rate(from_date, to_date)

            show_treeview(content, columns, rows, "HubLorryRate")

        except Exception as e:
            ctk.CTkLabel(
                frame, text=f"❌ Error: {str(e)}", 
                text_color="red"
            ).pack(pady=10)

    ctk.CTkButton(
        frame, 
        text="🚀 Generate Report", 
        command=generate
    ).pack(pady=40)