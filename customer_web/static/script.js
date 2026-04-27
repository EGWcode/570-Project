const menuItems = window.SOUL_DATA.menuItems;
const taxRate = window.SOUL_DATA.taxRate;
const categories = window.SOUL_DATA.categories;
const branches = window.SOUL_DATA.branches;
const dates = window.SOUL_DATA.dates;
const paymentTypes = window.SOUL_DATA.paymentTypes;
const cart = [];
let menuAvailability = {};

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

function renderMenu(category) {
    document.getElementById("category-title").textContent = category;
    const list = document.getElementById("menu-list");
    list.innerHTML = "";

    menuItems
        .filter((item) => item.category === category)
        .forEach((item) => {
            const card = document.createElement("article");
            const availability = menuAvailability[item.name];
            const soldOut = availability && availability.available === false;
            card.className = `menu-card${soldOut ? " sold-out" : ""}`;
            const priceMarkup = item.complimentary ? `<span class="price complimentary">Complimentary</span>` : `<span class="price">${money(item.price)}</span>`;
            let actionMarkup = `<button type="button" class="primary-btn">Add to Order</button>`;
            if (item.complimentary) {
                actionMarkup = `<span class="complimentary-note">Included with your meal</span>`;
            } else if (soldOut) {
                actionMarkup = `<button type="button" class="primary-btn" disabled>Sold Out</button>`;
            }
            card.innerHTML = `
                <div class="menu-card-top">
                    <h3>${item.name}</h3>
                    ${priceMarkup}
                </div>
                <p>${item.description}</p>
                <div class="menu-card-bottom">
                    <span class="tag">${item.tags}</span>
                    ${actionMarkup}
                </div>
            `;
            const addButton = card.querySelector("button");
            if (addButton && !soldOut) {
                addButton.addEventListener("click", () => addToCart(item));
            }
            list.appendChild(card);
        });
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
    categories.forEach((category, index) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `category-btn${index === 0 ? " active" : ""}`;
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
    cart.push(item);
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
            row.innerHTML = `<span>${item.name} - ${money(item.price)}</span><button type="button">Remove</button>`;
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
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
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
        data.times.forEach((time) => {
            const option = document.createElement("option");
            option.value = time;
            option.textContent = time;
            timeSelect.appendChild(option);
        });
        if (!data.times.length) {
            const option = document.createElement("option");
            option.value = "";
            option.textContent = "No times available";
            timeSelect.appendChild(option);
        }
    } catch (error) {
        showToast(error.message, true);
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

bootstrapControls();
renderMenu(categories[0]);
renderCart();
refreshReservationTimes();
refreshMenuAvailability();
