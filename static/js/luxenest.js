document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-auto-dismiss]").forEach((toast) => {
    const dismiss = () => {
      toast.classList.add("toast-hiding");
      window.setTimeout(() => toast.remove(), 260);
    };
    const timeout = Number(toast.dataset.autoDismiss || 5000);
    window.setTimeout(dismiss, timeout);
    toast.querySelector(".toast-close")?.addEventListener("click", dismiss);
  });

  document.querySelectorAll("[data-autocomplete]").forEach((input) => {
    const box = document.querySelector(input.dataset.autocomplete);
    input.addEventListener("input", async () => {
      const q = input.value.trim();
      if (q.length < 2) {
        box.innerHTML = "";
        box.classList.remove("show");
        return;
      }
      const res = await fetch(`/shop/suggest/?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      box.innerHTML = data.results.map((item) => `<a class="dropdown-item" href="/shop/product/${item.slug}/">${item.name}</a>`).join("");
      box.classList.toggle("show", data.results.length > 0);
    });
    document.addEventListener("click", (event) => {
      if (!input.closest(".search-form").contains(event.target)) {
        box.classList.remove("show");
      }
    });
  });

  const aiChat = document.querySelector("[data-ai-chat]");
  if (aiChat) {
    const panel = aiChat.querySelector("[data-ai-chat-panel]");
    const body = aiChat.querySelector("[data-ai-chat-body]");
    const form = aiChat.querySelector("[data-ai-chat-form]");
    const input = form?.querySelector("input[name='message']");
    const csrf = form?.querySelector("[name='csrfmiddlewaretoken']")?.value || "";

    const addMessage = (text, type = "bot") => {
      const bubble = document.createElement("div");
      bubble.className = `ai-message ${type}`;
      bubble.textContent = text;
      body.appendChild(bubble);
      body.scrollTop = body.scrollHeight;
      return bubble;
    };

    const addProducts = (products) => {
      if (!products?.length) return;
      const wrap = document.createElement("div");
      wrap.className = "ai-product-suggestions";
      wrap.innerHTML = products.map((product) => `
        <a class="ai-product-card" href="${product.url}">
          <img src="${product.image}" alt="${product.name}">
          <span><strong>${product.name}</strong><small>${product.price}</small></span>
        </a>
      `).join("");
      body.appendChild(wrap);
      body.scrollTop = body.scrollHeight;
    };

    const askAssistant = async (message) => {
      addMessage(message, "user");
      const thinking = addMessage("Checking LuxeNest for you...", "bot");
      try {
        const payload = new URLSearchParams({ message });
        const res = await fetch(form.action, {
          method: "POST",
          headers: { "X-CSRFToken": csrf, "Content-Type": "application/x-www-form-urlencoded" },
          body: payload,
        });
        const data = await res.json();
        thinking.textContent = data.reply;
        addProducts(data.products);
      } catch (_) {
        thinking.textContent = "I could not connect right now. Please try again in a moment.";
      }
    };

    aiChat.querySelector("[data-ai-chat-toggle]")?.addEventListener("click", () => {
      aiChat.classList.toggle("open");
      if (aiChat.classList.contains("open")) input?.focus();
    });
    aiChat.querySelector("[data-ai-chat-close]")?.addEventListener("click", () => aiChat.classList.remove("open"));
    aiChat.querySelectorAll("[data-ai-prompt]").forEach((button) => {
      button.addEventListener("click", () => askAssistant(button.dataset.aiPrompt));
    });
    form?.addEventListener("submit", (event) => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message) return;
      input.value = "";
      askAssistant(message);
    });
  }

  document.querySelectorAll("[data-pincode-check]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const pincode = form.querySelector("input").value;
      const output = form.querySelector("[data-output]");
      output.classList.add("skeleton");
      const res = await fetch(`/orders/delivery/check/?pincode=${encodeURIComponent(pincode)}`);
      const data = await res.json();
      output.classList.remove("skeleton");
      output.textContent = data.message;
      output.className = data.serviceable ? "text-success fw-bold" : "text-danger fw-bold";
    });
  });

  const deliveryMapNode = document.getElementById("delivery-map");
  if (deliveryMapNode && window.L) {
    const map = L.map("delivery-map").setView([22.9734, 78.6569], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);
    let marker = L.marker([22.9734, 78.6569]).addTo(map).bindPopup("LuxeNest India delivery network").openPopup();
    const result = document.querySelector("[data-delivery-result]");

    const updateMap = (lat, lng, label) => {
      map.setView([lat, lng], 12);
      marker.setLatLng([lat, lng]).bindPopup(label).openPopup();
    };

    document.querySelectorAll("[data-delivery-map-check]").forEach((form) => {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const pincode = form.querySelector("[name='pincode']").value.trim();
        result.className = "delivery-result mt-3 skeleton";
        const res = await fetch(`/orders/delivery/check/?pincode=${encodeURIComponent(pincode)}`);
        const data = await res.json();
        let locationLabel = pincode;
        try {
          const geo = await fetch(`https://nominatim.openstreetmap.org/search?format=json&countrycodes=in&postalcode=${encodeURIComponent(pincode)}&limit=1`);
          const places = await geo.json();
          if (places.length) {
            updateMap(Number(places[0].lat), Number(places[0].lon), `Pincode ${pincode}`);
            locationLabel = places[0].display_name;
          }
        } catch (_) {}
        result.className = data.serviceable ? "delivery-result mt-3 success" : "delivery-result mt-3 danger";
        result.innerHTML = data.serviceable
          ? `<strong>Delivery available</strong><span>${locationLabel}</span><span>Estimated delivery: ${data.eta}</span>`
          : `<strong>Not serviceable</strong><span>Please enter a valid Indian pincode.</span>`;
      });
    });

    document.querySelectorAll("[data-use-location]").forEach((button) => {
      button.addEventListener("click", () => {
        if (!navigator.geolocation) {
          result.className = "delivery-result mt-3 danger";
          result.textContent = "Location is not supported by this browser.";
          return;
        }
        navigator.geolocation.getCurrentPosition(
          (position) => {
            updateMap(position.coords.latitude, position.coords.longitude, "Your current location");
            result.className = "delivery-result mt-3 success";
            result.innerHTML = "<strong>Location detected</strong><span>Use the nearest address pincode during checkout for exact ETA.</span>";
          },
          () => {
            result.className = "delivery-result mt-3 danger";
            result.textContent = "Location permission was blocked.";
          }
        );
      });
    });
  }

  const addressMapNode = document.getElementById("address-map");
  if (addressMapNode && window.L) {
    const addressMap = L.map("address-map").setView([22.9734, 78.6569], 5);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(addressMap);
    let addressMarker = L.marker([22.9734, 78.6569]).addTo(addressMap).bindPopup("Select current location").openPopup();
    const status = document.querySelector("[data-address-location-result]");
    const setField = (name, value) => {
      const field = document.querySelector(`[name="${name}"]`);
      if (field && value) field.value = value;
    };
    document.querySelectorAll("[data-address-location]").forEach((button) => {
      button.addEventListener("click", () => {
        if (!navigator.geolocation) {
          status.textContent = "Your browser does not support current location.";
          status.className = "small text-danger mb-3";
          return;
        }
        status.textContent = "Detecting your current location...";
        status.className = "small text-muted mb-3";
        navigator.geolocation.getCurrentPosition(
          async (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            addressMap.setView([lat, lon], 15);
            addressMarker.setLatLng([lat, lon]).bindPopup("Your current delivery location").openPopup();
            try {
              const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`);
              const place = await res.json();
              const a = place.address || {};
              const city = a.city || a.town || a.village || a.suburb || a.county;
              const line1 = [a.house_number, a.road, a.neighbourhood || a.suburb].filter(Boolean).join(", ");
              const line2 = [a.city_district || a.county, a.state_district].filter(Boolean).join(", ");
              setField("line1", line1 || place.display_name);
              setField("line2", line2);
              setField("city", city);
              setField("state", a.state);
              setField("pincode", a.postcode);
              status.textContent = a.postcode ? `Location pinned. Detected pincode ${a.postcode}.` : "Location pinned. Please confirm your pincode before saving.";
              status.className = a.postcode ? "small text-success fw-bold mb-3" : "small text-warning fw-bold mb-3";
            } catch (_) {
              status.textContent = "Location pinned, but address lookup failed. Please fill details manually.";
              status.className = "small text-warning fw-bold mb-3";
            }
          },
          () => {
            status.textContent = "Location permission was blocked. You can still enter the address manually.";
            status.className = "small text-danger mb-3";
          }
        );
      });
    });
  }
});
