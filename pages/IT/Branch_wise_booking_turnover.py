import customtkinter as ctk
from tkcalendar import DateEntry
from reports.BranchWiseBookingTurnover import get_Branch_wise_booking_turnover
from ui.treeview import show_treeview
from utils.export_excel import set_report_period

def load_report(content):

    for widget in content.winfo_children():
        widget.destroy()

     # Simple main frame
    frame = ctk.CTkFrame(content, fg_color="transparent")
    frame.pack(pady=20, padx=20, fill="both", expand=True)

    # Title
    ctk.CTkLabel(
        frame, 
        text="📊 Branch Wise Booking Turnover", 
        font=ctk.CTkFont(size=20, weight="bold")
    ).pack(pady=20)

    # 3 Date Ranges - PROPER GRID ALIGNMENT
    date_entries = []
    
    for i in range(3):
        # Each range row
        row_frame = ctk.CTkFrame(frame)
        row_frame.pack(fill="x", pady=12)
        
        # Use GRID instead of pack side="left"
        row_frame.grid_columnconfigure(0, weight=1)
        row_frame.grid_columnconfigure(1, weight=0)
        row_frame.grid_columnconfigure(2, weight=0)
        row_frame.grid_columnconfigure(3, weight=0)
        row_frame.grid_columnconfigure(4, weight=0)
        
        # Heading
        headings = ["Quarter", "Next Month", "Current Month"]
        ctk.CTkLabel(
            row_frame, 
            text=headings[i],
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # From label
        ctk.CTkLabel(row_frame, text="From", font=ctk.CTkFont(size=14)).grid(row=0, column=1, padx=(40,10), pady=15)
        
        # From date entry
        from_entry = DateEntry(row_frame, date_pattern="dd-mm-yyyy", width=18, font=("Arial", 14))
        from_entry.grid(row=0, column=2, padx=5, pady=15)
        date_entries.append(from_entry)
        
        # To label  
        ctk.CTkLabel(row_frame, text="To", font=ctk.CTkFont(size=14)).grid(row=0, column=3, padx=(30,10), pady=15)
        
        # To date entry
        to_entry = DateEntry(row_frame, date_pattern="dd-mm-yyyy", width=18, font=("Arial", 14))
        to_entry.grid(row=0, column=4, padx=20, pady=15)
        date_entries.append(to_entry)

    def generate():
        try:
            dates = [entry.get() for entry in date_entries]
            
            # Unpack dates 
            q_from, q_to, nm_from, nm_to, cm_from, cm_to = dates
            
            # period for excel 
            set_report_period(q_from, cm_to)
            
            columns, rows = get_Branch_wise_booking_turnover(*dates)
            show_treeview(content, columns, rows, "BranchWisebooking")
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
