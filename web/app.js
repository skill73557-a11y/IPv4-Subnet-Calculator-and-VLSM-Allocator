const $ = (selector) => document.querySelector(selector);
const colors = ["#9d83eb", "#65a9ed", "#59c5a1", "#e0af66", "#df83a6", "#7d9bea"];

function showError(target, message = "") {
  target.textContent = message;
}

async function postJson(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The calculation could not be completed.");
  return result;
}

function renderSubnet(result) {
  const prefix = Number(result.prefix);
  const hostBits = 32 - prefix;
  $("#subnet-cidr-tag").textContent = `${result.network}/${prefix}`;
  $("#network-bit-count").textContent = `${prefix} BITS`;
  $("#host-bit-count").textContent = `${hostBits} BITS`;
  $("#bit-strip").replaceChildren(...Array.from({ length: 32 }, (_, index) => {
    const bit = document.createElement("span");
    bit.className = `bit-cell${index >= prefix ? " host" : ""}`;
    bit.style.animationDelay = `${Math.min(index, 20) * 8}ms`;
    bit.title = `${index < prefix ? "Network" : "Host"} bit ${index + 1}`;
    return bit;
  }));
  $("#network-address").textContent = result.network;
  $("#broadcast-address").textContent = result.broadcast;
  $("#host-range").innerHTML = "";
  const first = document.createElement("span");
  first.textContent = result.first_host;
  const arrow = document.createElement("span");
  arrow.textContent = "→";
  const last = document.createElement("span");
  last.textContent = result.last_host;
  $("#host-range").append(first, arrow, last);
  $("#range-subtitle").textContent = `${result.host_count} assignable ${result.host_count === 1 ? "address" : "addresses"}`;
  $("#subnet-mask").textContent = result.subnet_mask;
  $("#host-count").innerHTML = "";
  const hostCount = document.createElement("span");
  hostCount.textContent = result.host_count;
  const hostLabel = document.createElement("small");
  hostLabel.textContent = " hosts";
  $("#host-count").append(hostCount, hostLabel);
  $("#total-addresses").innerHTML = "";
  const total = document.createElement("span");
  total.textContent = result.total_addresses.toLocaleString();
  const addressLabel = document.createElement("small");
  addressLabel.textContent = " addresses";
  $("#total-addresses").append(total, addressLabel);
  $("#wildcard-mask").textContent = result.wildcard;
}

function addRequirement(name = "", hosts = "") {
  const row = document.createElement("div");
  row.className = "requirement-row";
  const nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.placeholder = "e.g. Engineering";
  nameInput.setAttribute("aria-label", "Network name");
  nameInput.value = name;
  const hostInput = document.createElement("input");
  hostInput.type = "number";
  hostInput.min = "1";
  hostInput.step = "1";
  hostInput.placeholder = "Hosts";
  hostInput.setAttribute("aria-label", "Required hosts");
  hostInput.value = hosts;
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "remove-row";
  remove.setAttribute("aria-label", "Remove network");
  remove.textContent = "×";
  remove.addEventListener("click", () => row.remove());
  row.append(nameInput, hostInput, remove);
  $("#requirements-list").append(row);
}

function renderAllocations(result) {
  const map = $("#allocation-map");
  map.replaceChildren();
  const total = result.total_addresses;
  const used = result.allocations.reduce((sum, item) => {
    const prefix = Number(item.cidr.split("/")[1]);
    return sum + 2 ** (32 - prefix);
  }, 0);

  result.allocations.forEach((item, index) => {
    const block = document.createElement("div");
    const size = 2 ** (32 - Number(item.cidr.split("/")[1]));
    block.className = `allocation-block${size / total < 0.045 ? " tiny" : ""}`;
    block.style.flex = `${size} 1 0%`;
    block.style.background = `linear-gradient(135deg, ${colors[index % colors.length]}cc, ${colors[index % colors.length]}66)`;
    block.style.borderColor = `${colors[index % colors.length]}bb`;
    block.title = `${item.name}: ${item.cidr} · ${size.toLocaleString()} addresses`;
    const label = document.createElement("span");
    label.textContent = `${item.name} /${item.cidr.split("/")[1]}`;
    block.append(label);
    map.append(block);
  });

  const remaining = Math.max(0, total - used);
  if (remaining > 0) {
    const free = document.createElement("div");
    free.className = "allocation-block allocation-free";
    free.style.flex = `${remaining} 1 0%`;
    free.title = `${remaining.toLocaleString()} unallocated addresses`;
    if (remaining / total > 0.045) {
      const label = document.createElement("span");
      label.textContent = "Available";
      free.append(label);
    }
    map.append(free);
  }
  $("#base-tag").textContent = result.base_cidr;
  const usedPercent = total ? (used / total) * 100 : 0;
  $("#space-summary").textContent = `${usedPercent.toFixed(1)}% used · ${remaining.toLocaleString()} free`;

  const rows = result.allocations.map((item, index) => {
    const row = document.createElement("tr");
    const values = [
      item.cidr,
      `${item.name} · ${Number(item.need).toLocaleString()} hosts`,
      `${item.first} – ${item.last}`,
      `${Number(item.usable).toLocaleString()} usable`,
    ];
    values.forEach((value, cellIndex) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      if (cellIndex === 0) cell.style.color = colors[index % colors.length];
      row.append(cell);
    });
    return row;
  });
  $("#allocation-rows").replaceChildren(...rows);
}

$("#subnet-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showError($("#subnet-error"));
  const button = event.currentTarget.querySelector(".primary-button span:first-child");
  button.textContent = "Calculating…";
  try {
    const result = await postJson("/api/subnet", { cidr: $("#subnet-cidr").value.trim() });
    renderSubnet(result);
  } catch (error) {
    showError($("#subnet-error"), error.message);
  } finally {
    button.textContent = "Calculate subnet";
  }
});

$("#add-requirement").addEventListener("click", () => addRequirement());
$("#vlsm-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  showError($("#vlsm-error"));
  const requirements = [...document.querySelectorAll(".requirement-row")].map((row) => {
    const inputs = row.querySelectorAll("input");
    return { name: inputs[0].value.trim(), hosts: Number(inputs[1].value) };
  });
  const button = event.currentTarget.querySelector(".primary-button span:first-child");
  button.textContent = "Allocating…";
  try {
    const result = await postJson("/api/vlsm", {
      base_cidr: $("#base-cidr").value.trim(),
      requirements,
    });
    renderAllocations(result);
  } catch (error) {
    showError($("#vlsm-error"), error.message);
  } finally {
    button.textContent = "Allocate subnets";
  }
});

function selectTab(tab) {
  const subnetSelected = tab === "subnet";
  $("#subnet-panel").classList.toggle("hidden", !subnetSelected);
  $("#vlsm-panel").classList.toggle("hidden", subnetSelected);
  $("#crumb-current").textContent = subnetSelected ? "SUBNET CALCULATOR" : "VLSM PLANNER";
  document.querySelectorAll("[data-tab]").forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle("active", button.classList.contains("nav-item") && active);
    button.classList.toggle("selected", button.classList.contains("tab-button") && active);
    if (button.classList.contains("tab-button")) button.setAttribute("aria-selected", String(active));
  });
}

document.querySelectorAll("[data-tab]").forEach((button) => {
  button.addEventListener("click", () => selectTab(button.dataset.tab));
});

addRequirement("LAN-A", 100);
addRequirement("LAN-B", 50);
addRequirement("LAN-C", 25);
addRequirement("WAN-1", 2);
addRequirement("WAN-2", 2);
$("#subnet-form").requestSubmit();
