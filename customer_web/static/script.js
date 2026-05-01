// __ static data — no template injection needed __
const taxRate = 0.08;
const paymentTypes = ["CASH", "CREDIT", "DEBIT", "GIFT_CARD", "MOBILE"];
const branches = [
    { branch_id: 1,  branch_name: "Soul by the Sea - Hampton" },
    { branch_id: 2,  branch_name: "Soul by the Sea - Norfolk" },
    { branch_id: 11, branch_name: "Soul by the Sea - Suffolk" },
    { branch_id: 12, branch_name: "Soul by the Sea - Virginia Beach" },
];
let categories = ["Appetizers", "Above Sea", "Sea Level", "Under the Sea", "Sides", "Drinks", "Desserts"];
const dates = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
});
const menuItems = [
    // Appetizers
    { name: "Bread or Cornbread Basket", category: "Appetizers", price: 0.00, description: "Complimentary bread service. Choose white, sourdough, wheat, or warm cornbread with honey butter.", tags: "Complimentary", complimentary: true, options: [{ name: "bread_choice", label: "Bread Service", choices: ["No Bread", "White Bread", "Sourdough Bread", "Wheat Bread", "Warm Cornbread with Honey Butter"] }] },
    { name: "Soul by the Sea Dip",       category: "Appetizers", price: 14.99, description: "Creamy seafood dip with crab, shrimp, and cheese served with pita or chips.", tags: "Signature" },
    { name: "Bayou Mussels",             category: "Appetizers", price: 15.99, description: "Mussels simmered in cajun garlic butter broth.", tags: "Signature" },
    { name: "Chicken Wings",             category: "Appetizers", price: 11.99, description: "5 wings with BBQ, buffalo, lemon pepper, or honey hot.", tags: "Popular", options: [{ name: "sauce", label: "Wing Sauce", choices: ["BBQ", "Buffalo", "Lemon Pepper", "Honey Hot"] }] },
    { name: "Soul Food Egg Rolls",       category: "Appetizers", price: 12.99, description: "Collard greens and mac & cheese filling.", tags: "Signature" },
    { name: "Fried Green Tomatoes",      category: "Appetizers", price:  9.99, description: "Crispy fried green tomatoes.", tags: "Classic" },
    { name: "Cajun Calamari",            category: "Appetizers", price: 12.99, description: "Seasoned fried calamari.", tags: "Spicy" },
    { name: "Crab Cakes",               category: "Appetizers", price: 16.99, description: "2 golden crab cakes.", tags: "Premium" },
    { name: "Shrimp Cocktail",           category: "Appetizers", price: 13.99, description: "Chilled shrimp with cocktail sauce.", tags: "Classic" },
    { name: "Loaded Fries",              category: "Appetizers", price: 10.99, description: "Fries topped with cheese, bacon, and soul sauce.", tags: "Shareable" },
    // Above Sea
    { name: "Burger",                    category: "Above Sea",  price: 14.99, description: "Classic or bacon cheeseburger with fries.", tags: "Classic", options: [{ name: "style", label: "Burger Style", choices: ["Classic Burger", "Bacon Cheeseburger"] }] },
    { name: "Mama's Fried Chicken",      category: "Above Sea",  price: 18.99, description: "Crispy fried chicken with sides.", tags: "Popular" },
    { name: "Smothered Turkey Wings",    category: "Above Sea",  price: 20.99, description: "Slow cooked in rich gravy.", tags: "Soul Food" },
    { name: "Jerk Chicken Plate",        category: "Above Sea",  price: 19.99, description: "Seasoned jerk chicken with sides.", tags: "Spicy" },
    { name: "BBQ Ribs",                  category: "Above Sea",  price: 24.99, description: "Slow cooked ribs with BBQ sauce.", tags: "Popular" },
    { name: "Ribeye Steak",              category: "Above Sea",  price: 34.99, description: "Grilled ribeye steak.", tags: "Premium" },
    { name: "Burnt Ends",                category: "Above Sea",  price: 22.99, description: "Tender BBQ beef bites.", tags: "BBQ" },
    { name: "Oxtail Plate",              category: "Above Sea",  price: 29.99, description: "Slow cooked oxtail with rice and gravy.", tags: "Premium" },
    // Sea Level
    { name: "Surf and Turf",             category: "Sea Level",  price: 34.99, description: "Steak with shrimp.", tags: "Premium" },
    { name: "Seafood Platter",           category: "Sea Level",  price: 32.99, description: "Fish, shrimp, and crab combo.", tags: "Popular" },
    { name: "The Soul Platter",          category: "Sea Level",  price: 29.99, description: "Fish, shrimp, and chicken with sides.", tags: "Signature" },
    { name: "Cajun Shrimp Scampi",       category: "Sea Level",  price: 21.99, description: "Pasta with shrimp or chicken.", tags: "Spicy", options: [{ name: "protein", label: "Protein", choices: ["Shrimp", "Chicken"] }] },
    { name: "Bay Breeze Alfredo",        category: "Sea Level",  price: 21.99, description: "Creamy alfredo with chicken or shrimp.", tags: "Signature", options: [{ name: "protein", label: "Protein", choices: ["Chicken", "Shrimp"] }] },
    { name: "Jerk Salmon Dinner",        category: "Sea Level",  price: 26.99, description: "Seasoned salmon with sides.", tags: "Spicy" },
    // Under the Sea
    { name: "Fried Fish Platter",        category: "Under the Sea", price: 21.99, description: "Catfish or whiting with sides.", tags: "Classic", options: [{ name: "fish", label: "Fish Choice", choices: ["Catfish", "Whiting"] }] },
    { name: "Shrimp Basket",             category: "Under the Sea", price: 18.99, description: "Fried shrimp with fries.", tags: "Popular" },
    { name: "Stuffed Salmon",            category: "Under the Sea", price: 26.99, description: "Salmon stuffed with crab.", tags: "Signature" },
    { name: "Lobster Mac and Cheese",    category: "Under the Sea", price: 27.99, description: "Mac and cheese with lobster.", tags: "Premium" },
    { name: "Grilled Salmon Plate",      category: "Under the Sea", price: 24.99, description: "Seasoned grilled salmon.", tags: "Healthy" },
    // Sides
    { name: "Mac & Cheese",              category: "Sides", price: 5.99, description: "Classic baked mac.", tags: "Popular" },
    { name: "Collard Greens",            category: "Sides", price: 5.99, description: "Slow cooked greens.", tags: "Soul Food" },
    { name: "Candied Yams",              category: "Sides", price: 5.99, description: "Sweet yams with cinnamon.", tags: "Sweet" },
    { name: "Yellow Rice",               category: "Sides", price: 3.99, description: "Seasoned rice.", tags: "Classic" },
    { name: "Cornbread",                 category: "Sides", price: 3.99, description: "Warm cornbread.", tags: "Classic" },
    { name: "Fries",                     category: "Sides", price: 3.99, description: "Crispy seasoned fries.", tags: "Classic" },
    { name: "Roasted Corn on the Cob",   category: "Sides", price: 4.99, description: "Grilled corn.", tags: "Classic" },
    { name: "Mashed Potatoes w/ Gravy",  category: "Sides", price: 5.99, description: "Creamy potatoes with gravy.", tags: "Classic" },
    { name: "Green Beans",               category: "Sides", price: 4.99, description: "Seasoned green beans.", tags: "Classic" },
    { name: "Rice & Gravy",              category: "Sides", price: 4.99, description: "Classic southern side.", tags: "Soul Food" },
    { name: "Baked Beans",               category: "Sides", price: 4.99, description: "Sweet baked beans.", tags: "BBQ" },
    { name: "Side Salad",                category: "Sides", price: 4.99, description: "Fresh mixed greens.", tags: "Fresh" },
    { name: "Sweet Potato Fries",        category: "Sides", price: 4.99, description: "Crispy sweet fries.", tags: "Sweet" },
    // Drinks
    { name: "Coca-Cola Products",        category: "Drinks", price: 2.99, description: "Coke, Sprite, Fanta, and more.", tags: "Non-Alcoholic" },
    { name: "Apple Juice",               category: "Drinks", price: 2.99, description: "Chilled apple juice.", tags: "Non-Alcoholic" },
    { name: "Orange Juice",              category: "Drinks", price: 2.99, description: "Fresh orange juice.", tags: "Non-Alcoholic" },
    { name: "Bottled Water",             category: "Drinks", price: 1.99, description: "Purified water.", tags: "Non-Alcoholic" },
    { name: "Blue Sea Lemonade",         category: "Drinks", price: 4.99, description: "Signature lemonade. Flavors: strawberry, peach, mango, passionfruit, pineapple.", tags: "Signature", options: [{ name: "flavor", label: "Flavor", choices: ["Strawberry", "Peach", "Mango", "Passionfruit", "Pineapple"] }] },
    { name: "Sweet Tea",                 category: "Drinks", price: 3.99, description: "Classic southern tea. Flavors: peach, mango, strawberry, passionfruit, pineapple.", tags: "Non-Alcoholic", options: [{ name: "flavor", label: "Flavor", choices: ["Classic", "Peach", "Mango", "Strawberry", "Passionfruit", "Pineapple"] }] },
    { name: "Unsweet Tea",               category: "Drinks", price: 3.99, description: "Unsweetened iced tea.", tags: "Non-Alcoholic", options: [{ name: "flavor", label: "Flavor", choices: ["Classic", "Peach", "Mango", "Strawberry", "Passionfruit", "Pineapple"] }] },
    { name: "Arnold Palmer",             category: "Drinks", price: 3.99, description: "Tea and lemonade mix.", tags: "Non-Alcoholic" },
    { name: "Blue Sea Margarita",        category: "Drinks", price: 10.99, description: "Signature tropical margarita.", tags: "21+" },
    { name: "Strawberry Margarita",      category: "Drinks", price: 10.99, description: "Strawberry flavored margarita.", tags: "21+" },
    { name: "Mango Margarita",           category: "Drinks", price: 10.99, description: "Mango margarita.", tags: "21+" },
    { name: "Classic Mojito",            category: "Drinks", price: 11.99, description: "Mint and lime cocktail.", tags: "21+" },
    { name: "Pineapple Mojito",          category: "Drinks", price: 11.99, description: "Pineapple twist.", tags: "21+" },
    { name: "Peach Whiskey Smash",       category: "Drinks", price: 11.99, description: "Whiskey with peach and citrus.", tags: "21+" },
    // Desserts
    { name: "Sweet Potato Pie",          category: "Desserts", price: 7.99, description: "Classic southern pie.", tags: "Classic" },
    { name: "Chocolate Cake",            category: "Desserts", price: 7.99, description: "Rich chocolate cake.", tags: "Sweet" },
    { name: "Cheesecake",                category: "Desserts", price: 7.99, description: "Creamy cheesecake.", tags: "Classic" },
    { name: "Grandma's Poundcake",       category: "Desserts", price: 8.99, description: "Served with ice cream.", tags: "Signature" },
    { name: "Banana Pudding",            category: "Desserts", price: 6.99, description: "Classic pudding dessert.", tags: "Soul Food" },
    { name: "Peach Cobbler",             category: "Desserts", price: 7.99, description: "Warm cobbler with ice cream.", tags: "Popular" },
    { name: "Bread Pudding",             category: "Desserts", price: 6.99, description: "Sweet baked dessert.", tags: "Classic" },
    { name: "Red Velvet Cake",           category: "Desserts", price: 7.99, description: "Classic red velvet.", tags: "Popular" },
    { name: "Ice Cream",                 category: "Desserts", price: 4.99, description: "Vanilla, chocolate, or butter pecan.", tags: "Sweet", options: [{ name: "flavor", label: "Flavor", choices: ["Vanilla", "Chocolate", "Butter Pecan"] }] },
];
const cart = [];
let menuAvailability = {};
let optionItem = null;

const money = (value) => `$${Number(value).toFixed(2)}`;

function showToast(message, isError = false) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.classList.toggle("error", isError);
    toast.classList.add("show");
    window.setTimeout(() => toast.classList.remove("show"), 5200);
}

function openModal(id) {
    document.getElementById(id).classList.add("open");
    document.getElementById(id).setAttribute("aria-hidden", "false");
}

function closeModal(modal) {
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
}

function optionSummary(item) {
    const selected = item.selected_options || {};
    return Object.entries(selected)
        .map(([label, value]) => `${label}: ${value}`)
        .join("; ");
}

function cartItemLabel(item) {
    const summary = optionSummary(item);
    return summary ? `${item.name} (${summary})` : item.name;
}

function renderMenu(category) {
    if (!categories.includes(category)) {
        category = categories[0];
    }
    document.getElementById("category-title").textContent = category;
    const list = document.getElementById("menu-list");
    list.innerHTML = "";

    const visible = menuItems.filter((item) => item.category === category);

    visible.forEach((item) => {
            const card = document.createElement("article");
            const availability = menuAvailability[item.name];
            const soldOut = availability && availability.available === false;
            card.className = `menu-card${soldOut ? " sold-out" : ""}`;
            const priceMarkup = item.complimentary ? `<span class="price complimentary">Complimentary</span>` : `<span class="price">${money(item.price)}</span>`;
            const soldOutMarkup = soldOut ? `<span class="sold-out-badge">Temporarily Unavailable</span>` : "";
            const soldOutNote = soldOut ? `<p class="sold-out-note">Temporarily Unavailable</p>` : "";
            let actionMarkup = `<button type="button" class="primary-btn">${item.options ? "Choose Options" : "Add to Order"}</button>`;
            if (soldOut) {
                actionMarkup = `<button type="button" class="primary-btn" disabled>Temporarily Unavailable</button>`;
            }
            card.innerHTML = `
                <div class="menu-card-top">
                    <h3>${item.name} ${soldOutMarkup}</h3>
                    ${priceMarkup}
                </div>
                <p>${item.description || "Freshly added menu item."}</p>
                ${soldOutNote}
                <div class="menu-card-bottom">
                    <span class="tag">${item.tags || "Menu Item"}</span>
                    ${actionMarkup}
                </div>
            `;
            const addButton = card.querySelector("button");
            if (addButton && !soldOut) {
                addButton.addEventListener("click", () => handleMenuAdd(item));
            }
            list.appendChild(card);
        });

    // Clickstream: log which items the customer browsed to MongoDB
    const branchId = branches.length > 0 ? branches[0].branch_id : null;
    fetch("/api/menu-view", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            branch_id: branchId,
            category: category,
            items: visible.map((i) => ({ name: i.name, item_id: i.item_id || null })),
        }),
    }).catch(() => {});
}

function handleMenuAdd(item) {
    if (item.options && item.options.length) {
        openOptionsModal(item);
    } else {
        addToCart(item);
    }
}

function openOptionsModal(item) {
    optionItem = item;
    const form = document.getElementById("options-form");
    const body = document.getElementById("options-fields");
    document.getElementById("options-item-name").textContent = item.name;
    document.getElementById("options-item-description").textContent = item.description;
    body.innerHTML = "";

    item.options.forEach((group) => {
        const label = document.createElement("label");
        label.textContent = group.label;
        const select = document.createElement("select");
        select.name = group.label;
        select.required = true;
        group.choices.forEach((choice) => {
            const option = document.createElement("option");
            option.value = choice;
            option.textContent = choice;
            select.appendChild(option);
        });
        label.appendChild(select);
        body.appendChild(label);
    });

    form.reset();
    openModal("options-modal");
}

async function refreshMenuAvailability() {
    try {
        const response = await fetch("/api/menu-availability?branch_id=1");
        const data = await response.json();
        if (response.ok && data.ok) {
            menuAvailability = data.availability || {};
            const active = document.querySelector(".category-btn.active");
            renderMenu(active ? active.dataset.category : categories[0]);
        }
    } catch (error) {
        menuAvailability = {};
    }
}

function fillSelect(select, rows, valueKey, labelKey, selectedValue = null) {
    select.innerHTML = "";
    rows.forEach((row) => {
        const option = document.createElement("option");
        option.value = row[valueKey];
        option.textContent = row[labelKey];
        if (String(row[valueKey]) === String(selectedValue)) {
            option.selected = true;
        }
        select.appendChild(option);
    });
}

function bootstrapControls() {
    const categoryWrap = document.getElementById("category-buttons");
    categoryWrap.innerHTML = "";
    const activeCategory = document.querySelector(".category-btn.active")?.dataset.category;
    const selectedCategory = categories.includes(activeCategory) ? activeCategory : categories[0];
    categories.forEach((category, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `category-btn${category === selectedCategory || (!selectedCategory && index === 0) ? " active" : ""}`;
        button.dataset.category = category;
        button.textContent = category;
        button.addEventListener("click", () => {
            document.querySelectorAll(".category-btn").forEach((btn) => btn.classList.remove("active"));
            button.classList.add("active");
            renderMenu(category);
        });
        categoryWrap.appendChild(button);
    });

    fillSelect(document.getElementById("reservation-branch"), branches, "branch_id", "branch_name");
    fillSelect(document.getElementById("review-branch"), branches, "branch_id", "branch_name");
    fillSelect(
        document.getElementById("reservation-date"),
        dates.map((date) => ({ date })),
        "date",
        "date"
    );
    fillSelect(
        document.getElementById("payment-type"),
        paymentTypes.map((paymentType) => ({ paymentType })),
        "paymentType",
        "paymentType",
        "CREDIT"
    );
}

function addToCart(item) {
    cart.push({ ...item });
    renderCart();
}

function renderCart() {
    const list = document.getElementById("cart-list");
    list.innerHTML = "";

    if (!cart.length) {
        list.innerHTML = `<div class="cart-empty">Your cart is empty.</div>`;
    } else {
        cart.forEach((item, index) => {
            const row = document.createElement("div");
            row.className = "cart-row";
            const priceText = item.complimentary ? "Complimentary" : money(item.price);
            const summary = optionSummary(item);
            row.innerHTML = `
                <span>
                    <strong>${item.name}</strong> - ${priceText}
                    ${summary ? `<small>${summary}</small>` : ""}
                </span>
                <button type="button">Remove</button>
            `;
            row.querySelector("button").addEventListener("click", () => {
                cart.splice(index, 1);
                renderCart();
            });
            list.appendChild(row);
        });
    }

    const total = cart.reduce((sum, item) => sum + Number(item.price), 0);
    document.getElementById("cart-total").textContent = money(total);
}

function paymentTotals() {
    const subtotal = cart.reduce((sum, item) => sum + Number(item.price), 0);
    const tax = Number((subtotal * taxRate).toFixed(2));
    return { subtotal, tax, total: subtotal + tax };
}

async function postJson(url, payload) {
    const options = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    };

    let response;
    try {
        response = await fetch(url, options);
    } catch {
        try {
            await new Promise((resolve) => window.setTimeout(resolve, 300));
            response = await fetch(`${window.location.origin}${url}`, options);
        } catch {
            throw new Error("Server connection was interrupted. Refresh the page and try again.");
        }
    }
    const text = await response.text();
    let data;
    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        data = {
            ok: false,
            message: response.status === 404
                ? "That action is not loaded yet. Fully restart main.py, then refresh this page."
                : "Request failed. Check the terminal for details.",
        };
    }
    if (!response.ok || !data.ok) {
        throw new Error(data.message || "Request failed.");
    }
    return data;
}

async function refreshReservationTimes() {
    const branch = document.getElementById("reservation-branch").value;
    const date = document.getElementById("reservation-date").value;
    const timeSelect = document.getElementById("reservation-time");
    timeSelect.innerHTML = "";

    try {
        const response = await fetch(`/api/reservation-times?branch_id=${encodeURIComponent(branch)}&date=${encodeURIComponent(date)}`);
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.message || "Could not load reservation times.");
        }
        fillReservationTimes(data.times);
    } catch (error) {
        fillReservationTimes(["11:00 AM", "12:00 PM", "1:00 PM", "5:00 PM", "6:00 PM", "7:00 PM"]);
    }
}

function fillReservationTimes(times) {
    const timeSelect = document.getElementById("reservation-time");
    timeSelect.innerHTML = "";
    times.forEach((time) => {
        const option = document.createElement("option");
        option.value = time;
        option.textContent = time;
        timeSelect.appendChild(option);
    });
    if (!times.length) {
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "No times available";
        timeSelect.appendChild(option);
    }
}

document.querySelectorAll("[data-open-modal]").forEach((button) => {
    button.addEventListener("click", () => openModal(button.dataset.openModal));
});

document.querySelectorAll("[data-close-modal]").forEach((button) => {
    button.addEventListener("click", () => closeModal(button.closest(".modal")));
});

document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("click", (event) => {
        if (event.target === modal) {
            closeModal(modal);
        }
    });
});

document.getElementById("clear-cart").addEventListener("click", () => {
    cart.length = 0;
    document.getElementById("notes").value = "";
    renderCart();
});

document.getElementById("options-form").addEventListener("submit", (event) => {
    event.preventDefault();
    if (!optionItem) {
        return;
    }
    const form = new FormData(event.currentTarget);
    const selectedOptions = Object.fromEntries(form.entries());
    addToCart({ ...optionItem, selected_options: selectedOptions });
    closeModal(document.getElementById("options-modal"));
    event.currentTarget.reset();
    optionItem = null;
});

document.getElementById("place-order").addEventListener("click", () => {
    if (!cart.length) {
        showToast("Please add at least one item before placing an order.", true);
        return;
    }

    const totals = paymentTotals();
    document.getElementById("payment-summary").textContent =
        `Subtotal: ${money(totals.subtotal)}   Tax: ${money(totals.tax)}   Total: ${money(totals.total)}`;
    openModal("payment-modal");
});

document.getElementById("reservation-branch").addEventListener("change", refreshReservationTimes);
document.getElementById("reservation-date").addEventListener("change", refreshReservationTimes);

document.getElementById("payment-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
        const data = await postJson("/api/orders", {
            cart,
            notes: document.getElementById("notes").value,
            payment: Object.fromEntries(form.entries()),
        });
        showToast(`Order #${data.order_id} paid and sent to the kitchen. Payment: ${data.payment_type}. Card: ${data.masked_card}. Total: ${money(data.total)}.`);
        cart.length = 0;
        document.getElementById("notes").value = "";
        formElement.reset();
        formElement.querySelector("[name='tip_amount']").value = "0.00";
        renderCart();
        await refreshMenuAvailability();
        closeModal(document.getElementById("payment-modal"));
    } catch (error) {
        showToast(error.message, true);
    }
});

document.getElementById("reservation-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
        const data = await postJson("/api/reservations", Object.fromEntries(form.entries()));
        showToast(data.message);
        closeModal(document.getElementById("reservation-modal"));
        formElement.reset();
        await refreshReservationTimes();
    } catch (error) {
        showToast(error.message, true);
    }
});

document.getElementById("review-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
        const data = await postJson("/api/reviews", Object.fromEntries(form.entries()));
        showToast(data.message);
        closeModal(document.getElementById("review-modal"));
        formElement.reset();
    } catch (error) {
        showToast(error.message, true);
    }
});

async function loadMenuFromDB() {
    try {
        const response = await fetch("/api/menu-items");
        const data = await response.json();
        if (data.ok && data.items && data.items.length > 0) {
            const staticItemsByName = new Map(menuItems.map(item => [item.name, item]));
            menuItems.length = 0;
            data.items.forEach(item => {
                const staticItem = staticItemsByName.get(item.name) || {};
                menuItems.push({ ...staticItem, ...item });
            });
            categories = [...new Set(menuItems.map(item => item.category).filter(Boolean))];
            bootstrapControls();
        }
    } catch (_) {}
}

bootstrapControls();
renderCart();
refreshReservationTimes();
loadMenuFromDB()
    .then(refreshMenuAvailability)
    .then(() => renderMenu(document.querySelector(".category-btn.active")?.dataset.category || categories[0]));

const params = new URLSearchParams(window.location.search);
if (params.get("reservation") === "confirmed") {
    showToast(`Reservation confirmed${params.get("id") ? ` #${params.get("id")}` : ""}.`);
    window.history.replaceState({}, document.title, window.location.pathname);
} else if (params.get("reservation_error")) {
    showToast(params.get("reservation_error"), true);
    window.history.replaceState({}, document.title, window.location.pathname);
}
