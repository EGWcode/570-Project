'''
customer_ui.py

    FLOW - Enterprise Restaurant Management System
    CSC 570 Sp 26'
    Created by Day Ekoi - April 23-24 2026

 This file is the Tkinter customer interface for the FLOW system.
 It provides the customer-facing portal for Soul by the Sea, including
 menu browsing, cart management, checkout flow, reservation access,
 and customer account actions.

Functions / Classes:
   - CustomerUI              : main Tkinter window for the customer portal
   - __init__()              : initializes window state, menu data, and layout
   - create_widgets()        : builds the main customer interface
   - show_menu_items()       : displays menu items by category
   - add_to_cart()           : adds a selected menu item to the cart
   - update_cart()           : refreshes cart totals and item display
   - checkout()              : handles customer checkout action

   !!!! Important Notes to self: connect frontend actions to backend/customer.py !!!!
'''


import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class CustomerUI(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("FLOW | Soul by the Sea Customer Portal")
        self.geometry("1200x760")
        self.configure(bg="#0a0a0f")

        self.cart = []
        self.current_category = "Appetizers"

        # ---------- UPDATED MENU ----------
        self.menu_items = [

        # APPETIZERS
        {"name":"Soul by the Sea Dip","category":"Appetizers","price":14.99,
         "description":"Creamy seafood dip with crab, shrimp, and cheese served with pita or tortilla chips.","tags":"Signature"},

        {"name":"Bayou Mussels","category":"Appetizers","price":15.99,
         "description":"Mussels simmered in cajun garlic butter broth.","tags":"Signature"},

        {"name":"Chicken Wings","category":"Appetizers","price":11.99,
         "description":"5 wings with BBQ, Buffalo, Lemon Pepper, or Honey Hot.","tags":"Popular"},

        {"name":"Soul Rolls","category":"Appetizers","price":12.99,
         "description":"Egg rolls stuffed with collard greens and mac & cheese.","tags":"Signature"},

        {"name":"Firecracker Shrimp","category":"Appetizers","price":13.99,
         "description":"Crispy shrimp tossed in a sweet-spicy glaze.","tags":"Spicy"},

        # ABOVE SEA
        {"name":"Burger","category":"Above Sea","price":14.99,
         "description":"Classic or bacon cheeseburger with fries.","tags":"Classic"},

        {"name":"Mama’s Fried Chicken","category":"Above Sea","price":18.99,
         "description":"Crispy fried chicken served with two sides.","tags":"Popular"},

        {"name":"Smothered Turkey Wings","category":"Above Sea","price":20.99,
         "description":"Slow cooked turkey wings in rich gravy.","tags":"Soul Food"},

        {"name":"BBQ Ribs","category":"Above Sea","price":24.99,
         "description":"Slow-cooked ribs with house BBQ sauce.","tags":"Popular"},

        {"name":"Oxtail Plate","category":"Above Sea","price":29.99,
         "description":"Tender oxtail served with rice and gravy.","tags":"Premium"},

        # SEA LEVEL
        {"name":"The Soul Platter","category":"Sea Level","price":29.99,
         "description":"Fish, shrimp, and chicken served with two sides.","tags":"Signature"},

        {"name":"Surf & Turf","category":"Sea Level","price":34.99,
         "description":"Steak with shrimp and sides.","tags":"Premium"},

        {"name":"Seafood Platter","category":"Sea Level","price":32.99,
         "description":"Fish, shrimp, and crab combo platter.","tags":"Popular"},

        {"name":"Bay Breeze Alfredo","category":"Sea Level","price":21.99,
         "description":"Creamy pasta with chicken or shrimp.","tags":"Signature"},

        # UNDER THE SEA
        {"name":"Fried Fish Platter","category":"Under the Sea","price":21.99,
         "description":"Catfish or whiting served with sides.","tags":"Classic"},

        {"name":"Shrimp Basket","category":"Under the Sea","price":18.99,
         "description":"Fried shrimp with fries.","tags":"Popular"},

        {"name":"Stuffed Salmon","category":"Under the Sea","price":26.99,
         "description":"Salmon stuffed with crab.","tags":"Signature"},

        {"name":"Lobster Mac","category":"Under the Sea","price":27.99,
         "description":"Mac and cheese with lobster.","tags":"Premium"},

        # SIDES
        {"name":"Mac & Cheese","category":"Sides","price":5.99,
         "description":"Classic baked mac and cheese.","tags":""},

        {"name":"Greens","category":"Sides","price":5.99,
         "description":"Slow cooked collard greens.","tags":""},

        {"name":"Candied Yams","category":"Sides","price":5.99,
         "description":"Sweet yams with cinnamon.","tags":""},

        {"name":"Fries","category":"Sides","price":3.99,
         "description":"Crispy seasoned fries.","tags":""},

        # DRINKS
        {"name":"Blue Sea Lemonade","category":"Drinks","price":4.99,
         "description":"Signature lemonade. Flavors: strawberry, peach, mango, passionfruit, pineapple.","tags":"Signature"},

        {"name":"Sweet Tea","category":"Drinks","price":3.99,
         "description":"Classic iced tea. Flavors: peach, mango, strawberry, passionfruit, pineapple.","tags":""},

        {"name":"Coca Cola Products","category":"Drinks","price":2.99,
         "description":"Coke, Sprite, Fanta, and more.","tags":""},

        {"name":"Juices","category":"Drinks","price":2.99,
         "description":"Apple or orange juice.","tags":""},

        {"name":"Blue Sea Margarita","category":"Drinks","price":10.99,
         "description":"Signature tropical margarita.","tags":"21+"},

        {"name":"Peach Whiskey Smash","category":"Drinks","price":11.99,
         "description":"Whiskey cocktail with peach and citrus.","tags":"21+"},

        # DESSERTS
        {"name":"Sweet Potato Pie","category":"Desserts","price":7.99,
         "description":"Classic southern pie.","tags":""},

        {"name":"Chocolate Cake","category":"Desserts","price":7.99,
         "description":"Rich chocolate cake.","tags":""},

        {"name":"Cheesecake","category":"Desserts","price":7.99,
         "description":"Classic cheesecake.","tags":""},

        {"name":"Grandma’s Poundcake","category":"Desserts","price":8.99,
         "description":"Served warm with ice cream.","tags":"Signature"},

        ]

        self.categories = [
            "Appetizers",
            "Above Sea",
            "Sea Level",
            "Under the Sea",
            "Sides",
            "Drinks",
            "Desserts"
        ]

        self.build_layout()
        self.show_menu_items("Appetizers")

    # ---------- UI SAME AS YOUR ORIGINAL ----------
    # (everything below stays the same — no changes needed)

    def build_layout(self):
        self.build_header()
        self.build_main_area()
        self.build_cart_panel()

    def build_header(self):
        header = tk.Frame(self, bg="#0d1b2a", height=88)
        header.pack(fill="x")

        tk.Label(header, text="Soul by the Sea",
                 font=("Georgia", 24, "bold"),
                 fg="#00bfa5", bg="#0d1b2a").pack(padx=20, pady=20)

    def build_main_area(self):
        self.content = tk.Frame(self, bg="#0a0a0f")
        self.content.pack(side="left", fill="both", expand=True)

        body = tk.Frame(self.content, bg="#0a0a0f")
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg="#0d1b2a", width=180)
        self.sidebar.pack(side="left", fill="y")

        for category in self.categories:
            tk.Button(self.sidebar, text=category,
                      command=lambda c=category: self.show_menu_items(c)
                      ).pack(fill="x")

        self.menu_frame = tk.Frame(body, bg="#0a0a0f")
        self.menu_frame.pack(side="left", fill="both", expand=True)

    def show_menu_items(self, category):
        for widget in self.menu_frame.winfo_children():
            widget.destroy()

        for item in self.menu_items:
            if item["category"] == category:
                tk.Label(self.menu_frame, text=item["name"],
                         fg="white", bg="#0a0a0f").pack()

                tk.Label(self.menu_frame, text=item["description"],
                         fg="#aaa", bg="#0a0a0f").pack()

                tk.Button(self.menu_frame, text="Add",
                          command=lambda i=item: self.add_to_cart(i)).pack()

    def build_cart_panel(self):
        self.cart_panel = tk.Frame(self, bg="#0a0a0f", width=250)
        self.cart_panel.pack(side="right", fill="y")

        self.cart_list = tk.Listbox(self.cart_panel)
        self.cart_list.pack(fill="both", expand=True)

    def add_to_cart(self, item):
        self.cart.append(item)
        self.cart_list.insert(tk.END, item["name"])


if __name__ == "__main__":
    app = CustomerUI()
    app.mainloop()
