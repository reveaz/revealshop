const tg = window.Telegram.WebApp;
tg.expand();

// Тестовые товары
const products = [
    { id: "item1", name: "Кроссовки Nike Air Force", price: 8500, category: "обувь", image: "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=400&q=80" },
    { id: "item2", name: "Худи Essentials", price: 6200, category: "одежда", image: "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=400&q=80" },
    { id: "item3", name: "Рюкзак Kånken", price: 4300, category: "сумки", image: "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400&q=80" },
    { id: "item4", name: "Apple AirPods Pro 2", price: 21500, category: "электроника", image: "https://images.unsplash.com/photo-1600294037681-c80b4cb5b434?w=400&q=80" }
];

let cart = {};

function init() {
    const catalog = document.getElementById('catalog');
    catalog.className = 'item-grid';

    products.forEach(p => {
        const card = document.createElement('div');
        card.className = 'item-card';
        card.id = `card-${p.id}`;

        card.innerHTML = `
            <img src="${p.image}" class="item-img" alt="${p.name}">
            <div class="item-title">${p.name}</div>
            <div class="item-price">${p.price.toLocaleString('ru-RU')} ₽</div>
            <button class="btn-add" onclick="add('${p.id}')">Добавить</button>
            <div class="item-controls">
                <button onclick="remove('${p.id}')">-</button>
                <span id="count-${p.id}">0</span>
                <button onclick="add('${p.id}')">+</button>
            </div>
        `;
        catalog.appendChild(card);
    });

    updateMainButton();
}

function add(id) {
    cart[id] = (cart[id] || 0) + 1;
    updateCard(id);
    updateMainButton();
    tg.HapticFeedback.impactOccurred('light');
}

function remove(id) {
    if (!cart[id]) return;
    cart[id] -= 1;
    if (cart[id] <= 0) delete cart[id];
    updateCard(id);
    updateMainButton();
    tg.HapticFeedback.impactOccurred('light');
}

function updateCard(id) {
    const card = document.getElementById(`card-${id}`);
    const countSpan = document.getElementById(`count-${id}`);
    
    if (cart[id] > 0) {
        card.classList.add('has-item');
        countSpan.innerText = cart[id];
    } else {
        card.classList.remove('has-item');
    }
}

function updateMainButton() {
    let total = 0;
    let count = 0;
    
    for (const [id, qty] of Object.entries(cart)) {
        const product = products.find(p => p.id === id);
        total += product.price * qty;
        count += qty;
    }

    if (count > 0) {
        tg.MainButton.text = `Оформить (${total.toLocaleString('ru-RU')} ₽)`;
        tg.MainButton.show();
    } else {
        tg.MainButton.hide();
    }
}

tg.MainButton.onClick(() => {
    // Формируем заказ
    const orderItems = [];
    for (const [id, qty] of Object.entries(cart)) {
        const product = products.find(p => p.id === id);
        orderItems.push({
            id: product.id,
            name: product.name,
            category: product.category,
            price: product.price,
            quantity: qty
        });
    }
    
    const payload = JSON.stringify({ type: 'cart', items: orderItems });
    tg.sendData(payload);
});

init();
