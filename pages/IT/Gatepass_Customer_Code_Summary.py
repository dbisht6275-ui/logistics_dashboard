import customtkinter as ctk
from tkcalendar import DateEntry
from reports.GatepassCustomerCodeSummary import get_Gatepass_customer_code_summary
from ui.treeview import show_treeview

def load_report(content):
    # Clear existing widgets
    for widget in content.winfo_children():
        widget.destroy()

    # Main frame
    frame = ctk.CTkFrame(content, fg_color="transparent")
    frame.pack(pady=20, padx=20, fill="both", expand=True)

    # Title
    ctk.CTkLabel(
        frame, 
        text="📊 Gatepass Customer Code Summary", 
        font=ctk.CTkFont(size=20, weight="bold")
    ).pack(pady=20)

    # -------------------
    # Single From-To Range
    # -------------------
    row_frame = ctk.CTkFrame(frame)
    row_frame.pack(fill="x", pady=12)

    row_frame.grid_columnconfigure(0, weight=1)
    row_frame.grid_columnconfigure(1, weight=0)
   

    # From label and entry
    ctk.CTkLabel(row_frame, text="From", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=20, pady=15, sticky="w")
    from_entry = DateEntry(row_frame, date_pattern="dd-mm-yyyy", width=18, font=("Arial", 14))
    from_entry.grid(row=0, column=1, padx=5, pady=15)

    # To label and entry
    ctk.CTkLabel(row_frame, text="To", font=ctk.CTkFont(size=14)).grid(row=0, column=2, padx=20, pady=15, sticky="w")
    to_entry = DateEntry(row_frame, date_pattern="dd-mm-yyyy", width=18, font=("Arial", 14))
    to_entry.grid(row=0, column=3, padx=5, pady=15)
    # CNGE Code label and entry
    ctk.CTkLabel(row_frame, text="CNGE Code (Optional)", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=20, pady=10, sticky="w")
    cnge_entry = ctk.CTkEntry(row_frame, width=100, font=("Arial", 14))
    cnge_entry.grid(row=1, column=1, padx=5, pady=10, columnspan=3, sticky="w")
    # Generate button function
    def generate():
        try:
            from_date = from_entry.get()
            to_date   = to_entry.get()
            cnge_code = cnge_entry.get().strip()  # get code from entry
            if cnge_code == "":
               cnge_code = None  # optional

            # Call the report function
            columns, rows = get_Gatepass_customer_code_summary(from_date, to_date, cnge_code)

            # Show report in Treeview
            show_treeview(content, columns, rows, "Gatepass Customer Code Summary")

        except Exception as e:
            ctk.CTkLabel(
                frame, text=f"❌ Error: {str(e)}", 
                text_color="red", font=ctk.CTkFont(size=14)
            ).pack(pady=10)

    # Generate Button
    btn = ctk.CTkButton(
        frame, 
        text="🚀 Generate Report", 
        command=generate, 
        height=50,
        font=ctk.CTkFont(size=18, weight="bold"),
        fg_color="#0070C0"
    )
    btn.pack(pady=40)