document.addEventListener("DOMContentLoaded", function () {
    // Tắt auto scroll restore của trình duyệt
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";

    const tabsSelector = '#dataEntryTabs button[data-bs-toggle="tab"]';

    // Hàm ép về đầu trang ở nhiều “nhịp” để thắng mọi restore/autofocus
    const forceToTop = () => {
        window.scrollTo(0, 0); // ngay lập tức
        requestAnimationFrame(() => window.scrollTo(0, 0)); // sau frame
        setTimeout(() => window.scrollTo(0, 0), 0); // macrotask tiếp theo (Safari)
    };

    // 1) Gắn listener TRƯỚC khi show tab (để reload cũng scroll-top sau khi tab hiển thị)
    document.querySelectorAll(tabsSelector).forEach((btn) => {
        btn.addEventListener("shown.bs.tab", (e) => {
            const target = e.target.getAttribute("data-bs-target");
            if (target) sessionStorage.setItem("dataEntryActiveTab", target);
            forceToTop();
        });
    });

    // 2) Khôi phục tab đã lưu (không dùng hash)
    const savedTab = sessionStorage.getItem("dataEntryActiveTab");
    if (savedTab) {
        const trigger = document.querySelector(
            `${tabsSelector}[data-bs-target="${savedTab}"]`
        );
        if (trigger && window.bootstrap) new bootstrap.Tab(trigger).show();
    }

    // 3) Luôn về đầu trang khi mới load và khi trang được phục hồi từ BFCache
    forceToTop();
    window.addEventListener("load", () => forceToTop(), { once: true });
    window.addEventListener("pageshow", (e) => {
        if (e.persisted) forceToTop(); // Safari/Firefox BFCache
    });

    // 4) Trước khi submit form, nhớ tab đang mở
    document.querySelectorAll("#dataEntryTabsContent form").forEach((form) => {
        form.addEventListener("submit", () => {
            const activeBtn = document.querySelector(
                "#dataEntryTabs .nav-link.active"
            );
            const target = activeBtn
                ? activeBtn.getAttribute("data-bs-target")
                : null;
            if (target) sessionStorage.setItem("dataEntryActiveTab", target);
        });
    });
});

/* --- Tab Nhà máy nước sạch --- */
document.addEventListener("DOMContentLoaded", function () {
    const cleanForm = document.getElementById("cleanWaterForm");
    if (!cleanForm) return;

    cleanForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        const dateVal = (cleanForm.querySelector('input[name="date"]') || {}).value;

        // Các field cần kiểm tra
        const fieldNames = [
            "electricity",
            "pac_usage",
            "naoh_usage",
            "polymer_usage",
            "clean_water_output",
            "raw_water_jasan",
        ];
        const labels = {
            electricity: "Điện tiêu thụ (kWh)",
            pac_usage: "PAC (kg)",
            naoh_usage: "Xút (kg)",
            polymer_usage: "Polymer (kg)",
            clean_water_output: "Nước sạch sản xuất (m³)",
            raw_water_jasan: "Nước thô Jasan (m³)",
        };

        // Chỉ liệt kê các ô đã nhập (kể cả "0")
        const filled = fieldNames
            .map((n) => {
                const el = cleanForm.querySelector(`[name="${n}"]`);
                const v = el ? (el.value || "").trim() : "";
                return v === "" ? null : `- ${labels[n] || n}: ${v}`;
            })
            .filter(Boolean);

        if (!dateVal || filled.length === 0) {
            cleanForm.submit();
            return;
        }

        try {
            // Gọi API kiểm tra tồn tại theo ngày
            const url = `${window.DATA_ENTRY_CONFIG.cleanWaterExists
                }?date=${encodeURIComponent(dateVal)}`;
            const res = await fetch(url, { credentials: "same-origin" });
            const data = await res.json();
            
            //đóng để block update
            // if (data.exists) {
            //     const ok = window.confirm(
            //         `Đã có dữ liệu ngày ${dateVal} cho Nhà máy nước sạch.\n` +
            //         `Bạn sắp ghi đè các trường sau:\n${filled.join("\n")}\n\nTiếp tục?`
            //     );
            //     if (!ok) return;
            //     // Set cờ ghi đè để backend cho phép cập nhật
            //     const ow =
            //         document.getElementById("overwrite-flag") ||
            //         cleanForm.querySelector('input[name="overwrite"]');
            //     if (ow) ow.value = "1";
            // }
            if (data.exists) {
                showLockedInfo(`Đã có dữ liệu ngày ${dateVal} cho Nhà máy nước sạch. Bản ghi đã bị khóa, không thể chỉnh sửa.`);
                return;
            } else {
                const ok = await showConfirmFirstSave({
                    entity: 'Nhà máy nước sạch',
                    date: dateVal,
                    lines: filled // chính là mảng "- Nhãn: giá trị"
                });
                if (!ok) return;
            }
        } catch (_) {
            /* ignore lỗi mạng, vẫn submit */
        }

        cleanForm.submit();
    });
});

/* Helpers chung */
function getFilledNumericFields(form, names, labelsMap) {
    // Trả danh sách {name, label, value} với các input có nhập (kể cả "0")
    const out = [];
    for (const n of names) {
        const el = form.querySelector(`[name="${n}"]`);
        if (!el) continue;
        const raw = (el.value || "").trim();
        if (raw === "") continue;
        out.push({ name: n, label: labelsMap[n] || n, value: raw });
    }
    return out;
}

/* --- Tab Giếng khoan --- */
document.addEventListener("DOMContentLoaded", function () {
    const wellForm = document.getElementById("wellForm");
    if (wellForm) {
        wellForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            const dateVal = (wellForm.querySelector('input[name="date"]') || {})
                .value;
            const allIds = Array.from(
                wellForm.querySelectorAll('input[name="well_ids"]')
            ).map((i) => i.value);

            // Lọc các giếng đã nhập (kể cả "0")
            const filled = allIds
                .map((id) => {
                    const el = wellForm.querySelector(`input[name="production_${id}"]`);
                    const raw = el ? (el.value || "").trim() : "";
                    return raw === "" ? null : { id: Number(id), value: raw };
                })
                .filter(Boolean);

            if (!dateVal || filled.length === 0) {
                wellForm.submit();
                return;
            }

            // Gọi API kiểm tra chỉ với các giếng đã nhập
            const idsParam = filled.map((f) => f.id).join(",");
            try {
                const url = `${window.DATA_ENTRY_CONFIG.wellProductionExists
                    }?date=${encodeURIComponent(dateVal)}&well_ids=${encodeURIComponent(
                        idsParam
                    )}`;
                const res = await fetch(url, { credentials: "same-origin" });
                const data = await res.json();

                // if (data.exists && Array.isArray(data.wells) && data.wells.length) {
                //     // Lấy danh sách giếng đã nhập và đã có dữ liệu -> sẽ ghi đè
                //     const existingSet = new Set(data.wells.map(Number));
                //     const toOverwrite = filled.filter((f) => existingSet.has(f.id));
                //     if (toOverwrite.length) {
                //         const lines = toOverwrite
                //             .map((f) => `- Giếng ${f.id}: ${f.value} m³`)
                //             .join("\n");
                //         const ok = window.confirm(
                //             `Đã có dữ liệu ngày ${dateVal} cho một số giếng.\n` +
                //             `Bạn sắp ghi đè các giếng sau:\n${lines}\n\nTiếp tục?`
                //         );
                //         if (!ok) return;
                //         // Gửi danh sách giếng cần ghi đè
                //         document.getElementById("overwrite-ids").value = toOverwrite
                //             .map((f) => f.id)
                //             .join(",");
                //     }
                // }
                if (data.exists && Array.isArray(data.wells) && data.wells.length) {
                    showLockedInfo(`Đã có dữ liệu ngày ${dateVal} cho các giếng: ${data.wells.join(', ')}. Bản ghi đã bị khóa, không thể chỉnh sửa.`);
                    return;
                } else {
                    const lines = filled.map(f => {
                        // 🔹 Tìm phần tử tiêu đề <h6 class="card-title"> của giếng này
                        const wellCard = wellForm.querySelector(`input[name="production_${f.id}"]`)?.closest('.card');
                        const title = wellCard?.querySelector('.card-title')?.textContent.trim() || `Giếng ${f.id}`;
                        return `- ${title}: ${f.value} m³`;
                    });
                    const ok = await showConfirmFirstSave({
                        entity: 'Giếng khoan',
                        date: dateVal,
                        lines
                    });
                    if (!ok) return;
                }
            } catch (_) {
                /* bỏ qua lỗi mạng, vẫn submit */
            }

            wellForm.submit();
        });
    }
});

/* --- Tab Nước thải (NMNT 1/2) --- */
function hasAnyValue(form, names) {
    return names.some((n) => {
        const el = form.querySelector(`[name="${n}"]`);
        const v = el ? (el.value || "").trim() : "";
        return v !== "";
    });
}

async function attachWastewaterFormHandler(formId, overwriteId, plantNumber) {
    const form = document.getElementById(formId);
    if (!form) return;

    // Map tên input -> nhãn hiển thị
    const numericFields = [
        "wastewater_meter",
        "input_flow_tqt",
        "output_flow_tqt",
        "sludge_output",
        "electricity",
        "chemical_usage",
    ];
    const labelsMap = {
        wastewater_meter: "Đồng hồ nước thải",
        input_flow_tqt: "Lưu lượng đầu vào TQT",
        output_flow_tqt: "Lưu lượng đầu ra TQT",
        sludge_output: "Bùn thải",
        electricity: "Điện năng",
        chemical_usage: "Hóa chất",
    };

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        const dateVal = (form.querySelector('input[name="date"]') || {}).value;

        // Chỉ kiểm tra khi có nhập ít nhất một trường
        const filled = getFilledNumericFields(form, numericFields, labelsMap);
        if (!dateVal || filled.length === 0) {
            form.submit();
            return;
        }

        try {
            const url = `${window.DATA_ENTRY_CONFIG.wastewaterExists
                }?date=${encodeURIComponent(dateVal)}&plant_numbers=${plantNumber}`;
            const res = await fetch(url, { credentials: "same-origin" });
            const data = await res.json();

            // if (
            //     data.exists &&
            //     Array.isArray(data.plants) &&
            //     data.plants.includes(plantNumber)
            // ) {
            //     const lines = filled.map((f) => `- ${f.label}: ${f.value}`).join("\n");
            //     const ok = window.confirm(
            //         `Đã có dữ liệu ngày ${dateVal} cho Nhà máy nước thải ${plantNumber}.\n` +
            //         `Bạn sắp ghi đè các trường sau:\n${lines}\n\nTiếp tục?`
            //     );
            //     if (!ok) return;
            //     document.getElementById(overwriteId).value = "1";
            // }
            if (data.exists && Array.isArray(data.plants) && data.plants.includes(plantNumber)){
                showLockedInfo(`Đã có dữ liệu ngày ${dateVal} cho NMNT ${plantNumber}. Bản ghi đã bị khóa, không thể chỉnh sửa.`);
                return;
            } else {
                const lines = filled.map(f => `- ${f.label}: ${f.value}`);
                const ok = await showConfirmFirstSave({
                    entity: `NMNT ${plantNumber}`,
                    date: dateVal,
                    lines
                });
                if (!ok) return;
            }
        } catch (_) {
            /* ignore mạng */
        }

        form.submit();
    });
}

document.addEventListener("DOMContentLoaded", function () {
    attachWastewaterFormHandler("wastewaterForm1", "overwrite-wastewater-1", 1);
    attachWastewaterFormHandler("wastewaterForm2", "overwrite-wastewater-2", 2);
});

/* --- Tab Khách hàng --- */
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("customerForm");
    if (!form) return;

    // Filtering: search by company/contact + filter by type (daily/monthly)
    const searchEl = document.getElementById("customer-search");
    const filterEl = document.getElementById("customer-filter");
    const tbodySelector = "#customer-table-body .customer-row";

    function applyCustomerFilters() {
        const term =
            searchEl && searchEl.value ? searchEl.value.toLowerCase().trim() : "";
        const type = (filterEl && filterEl.value) || "";
        const rows = document.querySelectorAll(tbodySelector);
        rows.forEach((row) => {
            const dailyRaw = (row.dataset.daily || "").toLowerCase();
            const isDaily = dailyRaw === "true" || dailyRaw === "1";
            const matchesType = !type || (type === "daily" ? isDaily : !isDaily);
            const text0 =
                row.cells && row.cells[0] ? row.cells[0].textContent.toLowerCase() : "";
            const matchesSearch = !term || text0.includes(term);
            row.style.display = matchesType && matchesSearch ? "" : "none";
        });
    }

    if (searchEl) searchEl.addEventListener("input", applyCustomerFilters);
    if (filterEl) filterEl.addEventListener("change", applyCustomerFilters);
    // Initial run
    applyCustomerFilters();

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        const dateVal = (form.querySelector('input[name="date"]') || {}).value;

        const ids = Array.from(form.querySelectorAll('input[name="customer_ids"]'))
            .map((i) => Number(i.value))
            .filter(Boolean);

        const filled = ids
            .map((id) => {
                const cw = (
                    form.querySelector(`input[name="clean_water_${id}"]`)?.value || ""
                ).trim();
                const ww = (
                    form.querySelector(`input[name="wastewater_${id}"]`)?.value || ""
                ).trim();
                return cw !== "" || ww !== "" ? { id, cw, ww } : null;
            })
            .filter(Boolean);

        if (!dateVal || filled.length === 0) {
            form.submit();
            return;
        }

        try {
            const url = `${window.DATA_ENTRY_CONFIG.customerReadingsExists
                }?date=${encodeURIComponent(dateVal)}&customer_ids=${encodeURIComponent(
                    filled.map((x) => x.id).join(",")
                )}`;
            const res = await fetch(url, { credentials: "same-origin" });
            const data = await res.json();

            // if (
            //     data.exists &&
            //     Array.isArray(data.customers) &&
            //     data.customers.length
            // ) {
            //     const existSet = new Set(data.customers.map(Number));
            //     const toOverwrite = filled.filter((f) => existSet.has(f.id));
            //     if (toOverwrite.length) {
            //         const lines = toOverwrite
            //             .map((it) => {
            //                 const parts = [];
            //                 if (it.cw !== "") parts.push(`- Nước sạch: ${it.cw}`);
            //                 if (it.ww !== "") parts.push(`- Nước thải: ${it.ww}`);
            //                 return `KH ${it.id}:\n${parts.join("\n")}`;
            //             })
            //             .join("\n");
            //         const ok = window.confirm(
            //             `Đã có dữ liệu ngày ${dateVal} cho một số khách hàng.\n` +
            //             `Bạn sắp ghi đè dữ liệu cho các khách hàng sau:\n\n${lines}\n\nTiếp tục?`
            //         );
            //         if (!ok) return;
            //         document.getElementById("overwrite-customer-ids").value = toOverwrite
            //             .map((x) => x.id)
            //             .join(",");
            //     }
            // }
            if (data.exists && Array.isArray(data.customers) && data.customers.length){
                showLockedInfo(`Đã có dữ liệu ngày ${dateVal} cho một số khách hàng (${data.customers.join(', ')}). Bản ghi đã bị khóa, không thể chỉnh sửa.`);
                return;
            } else {
                const lines = filled.map(it => {
                    const parts = [];
                    if (it.cw !== '') parts.push(`- Nước sạch: ${it.cw}`);
                    if (it.ww !== '') parts.push(`- Nước thải: ${it.ww}`);

                    // 🔹 Lấy tên khách hàng từ hàng chứa input có id tương ứng
                    const row = form.querySelector(`input[name="customer_ids"][value="${it.id}"]`)?.closest('tr');
                    const name =
                        row?.querySelector('td strong')?.textContent.trim() ||
                        `KH ${it.id}`;

                    return `${name}:\n${parts.join('\n')}`;
                });

                const ok = await showConfirmFirstSave({
                    entity: 'Khách hàng',
                    date: dateVal,
                    lines,
                });
                if (!ok) return;
            }

        } catch (_) {
            /* ignore */
        }

        form.submit();
    });
});

/* --- Tab Bể chứa: xác nhận ghi đè --- */
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("tanksForm");
    if (!form) return;

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        const dateVal = (form.querySelector('input[name="date"]') || {}).value;
        const entries = Array.from(form.querySelectorAll('input[name^="level_"]'))
            .map((inp) => ({
                id: Number(inp.name.split("_")[1]),
                raw: (inp.value || "").trim(),
            }))
            .filter((x) => x.raw !== "" && !Number.isNaN(x.id));

        if (!dateVal || entries.length === 0) {
            form.submit();
            return;
        }

        try {
            const idsParam = entries.map((x) => x.id).join(",");
            const url = `${window.DATA_ENTRY_CONFIG.tankLevelExists
                }?date=${encodeURIComponent(dateVal)}&tank_ids=${encodeURIComponent(
                    idsParam
                )}`;
            const res = await fetch(url, { credentials: "same-origin" });
            const data = await res.json();
            // if (data.exists && Array.isArray(data.tanks) && data.tanks.length) {
            //     const existSet = new Set(data.tanks.map(Number));
            //     const toOverwrite = entries.filter((x) => existSet.has(x.id));
            //     if (toOverwrite.length) {
            //         const lines = toOverwrite
            //             .map((x) => `- Bể ${x.id}: ${x.raw} m³`)
            //             .join("\n");
            //         const ok = window.confirm(
            //             `Đã có dữ liệu ngày ${dateVal} cho một số bể chứa.\n` +
            //             `Bạn sắp ghi đè mức nước cho:\n${lines}\n\nTiếp tục?`
            //         );
            //         if (!ok) return;
            //     }
            // }
            if (data.exists && Array.isArray(data.tanks) && data.tanks.length) {
                showLockedInfo(`Đã có dữ liệu ngày ${dateVal} cho một số bể (${data.tanks.join(', ')}). Bản ghi đã bị khóa, không thể chỉnh sửa.`);
                return;
            } else {
                const lines = entries.map(x => `- Bể ${x.id}: ${x.raw} m³`);
                const ok = await showConfirmFirstSave({
                    entity: 'Bể chứa',
                    date: dateVal,
                    lines
                });
                if (!ok) return;
            }

        } catch (_) {
            /* ignore lỗi mạng, vẫn submit */
        }

        form.submit();
    });
});

// --- Progress bar BỂ CHỨA theo % ---
(function () {
    // Cập nhật 1 thanh theo giá trị nhập
    function updateTankBar(tankId, rawValue) {
        const bar = document.querySelector(
            `.progress-bar[data-tank-id="${tankId}"]`
        );
        if (!bar) return;

        const capacity = parseFloat(bar.dataset.capacity) || 0;
        const val = Math.max(0, parseFloat(rawValue));
        const pct = capacity > 0 && isFinite(val) ? (val / capacity) * 100 : 0;

        const pctStr = `${Math.round(pct)}%`;
        bar.style.width = pctStr;
        bar.textContent = pctStr;

        // A11y + trạng thái
        bar.setAttribute("aria-valuemin", "0");
        bar.setAttribute("aria-valuemax", "100");
        bar.setAttribute("aria-valuenow", String(Math.round(pct)));

        // Đổi màu cảnh báo (tuỳ ý)
        bar.classList.toggle("bg-danger", val > capacity);
        bar.classList.toggle("bg-warning", val > 0 && val < capacity * 0.1);
    }

    // Lắng nghe mọi ô input level_*
    function bindTankInputs(scope = document) {
        scope.querySelectorAll('input[name^="level_"]').forEach((inp) => {
            // cập nhật khi gõ
            inp.addEventListener("input", () => {
                const tankId = inp.name.split("_")[1];
                updateTankBar(tankId, inp.value);
            });
            // khởi tạo nếu có sẵn value (VD: back/forward cache hoặc autofill)
            if (inp.value !== "") {
                const tankId = inp.name.split("_")[1];
                updateTankBar(tankId, inp.value);
            }
        });
    }

    // Chạy khi DOM xong
    document.addEventListener("DOMContentLoaded", () => {
        // Nếu tab Tanks đang ACTIVE lúc load, bind ngay
        const tanksPane = document.querySelector("#tanks");
        if (tanksPane && tanksPane.classList.contains("active")) {
            bindTankInputs(tanksPane);
        }

        // Khi đổi tab sang Bể chứa thì mới bind (tránh làm thừa ở tab ẩn)
        document
            .querySelectorAll('#dataEntryTabs button[data-bs-toggle="tab"]')
            .forEach((btn) => {
                btn.addEventListener("shown.bs.tab", (e) => {
                    if (e.target.getAttribute("data-bs-target") === "#tanks") {
                        bindTankInputs(document.querySelector("#tanks"));
                    }
                });
            });
    });
})();

// Handle cho api lấy lịch sử nhập liệu giếng khoan
(function () {
    const els = {
        head: document.getElementById("wells-head"),
        body: document.getElementById("wells-body"),
        sum: document.getElementById("wells-summary"),
        pag: document.getElementById("wells-pagination"),
        range: document.getElementById("wells-range"),
    };
    if (!els.head) return;

    let page = 1;

    async function loadWells(pageArg = 1) {
        page = pageArg;
        const rangeDays = parseInt(els.range.value || "30", 10);
        const params = new URLSearchParams({ page, range_days: rangeDays });

        els.body.innerHTML = `<tr><td class="text-center py-3" colspan="999">Đang tải...</td></tr>`;

        try {
            const res = await fetch(
                `/api/well-productions/history/pivot?${params.toString()}`
            );
            const data = await res.json();
            const cols = data.columns || ["date"];
            const rows = data.rows || [];
            const meta = data.meta || { page: 1, pages: 1 };

            // header
            els.head.innerHTML = cols
                .map((c) => `<th>${c === "date" ? "Ngày" : c}</th>`)
                .join("");

            // body
            if (!rows.length) {
                els.body.innerHTML = `<tr><td class="text-center py-3" colspan="${cols.length}">Không có dữ liệu</td></tr>`;
            } else {
                els.body.innerHTML = rows
                    .map((r) => {
                        const tds = cols
                            .map((c) =>
                                c === "date"
                                    ? `<td>${r[c] || ""}</td>`
                                    : `<td>${typeof r[c] === "number"
                                        ? r[c].toLocaleString("vi-VN")
                                        : r[c] ?? ""
                                    }</td>`
                            )
                            .join("");
                        return `<tr>${tds}</tr>`;
                    })
                    .join("");
            }

            els.sum.textContent = `Trang ${meta.page}/${meta.pages || 1}`;
            buildPag(meta.page, meta.pages || 1);
        } catch (e) {
            console.error(e);
            els.body.innerHTML = `<tr><td class="text-danger text-center py-3" colspan="999">Lỗi tải dữ liệu</td></tr>`;
            els.sum.textContent = "—";
            els.pag.innerHTML = "";
        }
    }

    function buildPag(cur, total) {
        const maxButtons = 5;
        let start = Math.max(1, cur - Math.floor(maxButtons / 2));
        let end = start + maxButtons - 1;
        if (end > total) {
            end = total;
            start = Math.max(1, end - maxButtons + 1);
        }

        const prevDis = cur <= 1 ? " disabled" : "";
        const nextDis = cur >= total ? " disabled" : "";

        let html = `
        <li class="page-item${prevDis}">
            <a class="page-link" href="#" data-page="${cur - 1}">&laquo;</a>
        </li>`;
        for (let p = start; p <= end; p++) {
            const act = p === cur ? " active" : "";
            html += `<li class="page-item${act}"><a class="page-link" href="#" data-page="${p}">${p}</a></li>`;
        }
        html += `
        <li class="page-item${nextDis}">
            <a class="page-link" href="#" data-page="${cur + 1}">&raquo;</a>
        </li>`;

        els.pag.innerHTML = html;
        els.pag.querySelectorAll("a.page-link").forEach((a) => {
            a.addEventListener("click", (ev) => {
                ev.preventDefault();
                const target = parseInt(a.getAttribute("data-page"), 10);
                if (!isNaN(target)) loadWells(target);
            });
        });
    }

    els.range.addEventListener("change", () => loadWells(1));

    // chỉ load khi tab Giếng mở
    document.addEventListener("DOMContentLoaded", () => {
        const btn = document.querySelector("#wells-tab");
        const pane = document.querySelector("#wells");
        if (pane?.classList.contains("active")) loadWells(1);
        btn?.addEventListener("shown.bs.tab", () => loadWells(1));
    });
})();

// Handle cho api lấy lịch sử nhập liệu nước sạch
(function () {
    const els = {
        head: document.getElementById("cw-head"),
        body: document.getElementById("cw-body"),
        sum: document.getElementById("cw-summary"),
        pag: document.getElementById("cw-pagination"),
        range: document.getElementById("cw-range"),
    };
    if (!els.head) return;

    function headerMap(key) {
        switch (key) {
            case "date":
                return "Ngày";
            case "electricity":
                return "Điện tiêu thụ (kWh)";
            case "pac_usage":
                return "PAC (kg)";
            case "naoh_usage":
                return "Xút (kg)";
            case "polymer_usage":
                return "Polymer (kg)";
            case "clean_water_output":
                return "Nước sạch sản xuất (m³)";
            case "raw_water_jasan":
                return "Nước thô cấp cho Jasan (m³)";
            default:
                return key;
        }
    }

    let page = 1;

    async function loadCW(pageArg = 1) {
        page = pageArg;
        const rangeDays = parseInt(els.range.value || "30", 10);
        const params = new URLSearchParams({ page, range_days: rangeDays });

        els.body.innerHTML = `<tr><td class="text-center py-3" colspan="7">Đang tải...</td></tr>`;

        try {
            const res = await fetch(
                `/api/clean-water/consumption/history?${params.toString()}`
            );
            const data = await res.json();

            const cols = data.columns || ["date"];
            const rows = data.rows || [];
            const meta = data.meta || {
                page: 1,
                pages: 1,
                total: 0,
                range_days: rangeDays,
            };

            // header
            els.head.innerHTML = cols.map((c) => `<th>${headerMap(c)}</th>`).join("");

            // body
            if (!rows.length) {
                els.body.innerHTML = `<tr><td class="text-center py-3" colspan="${cols.length}">Không có dữ liệu</td></tr>`;
            } else {
                els.body.innerHTML = rows
                    .map((r) => {
                        const tds = cols
                            .map((c) =>
                                c === "date"
                                    ? `<td>${r[c] || ""}</td>`
                                    : `<td>${typeof r[c] === "number"
                                        ? r[c].toLocaleString("vi-VN")
                                        : r[c] ?? ""
                                    }</td>`
                            )
                            .join("");
                        return `<tr>${tds}</tr>`;
                    })
                    .join("");
            }

            els.sum.textContent = `${(meta.total || 0).toLocaleString(
                "vi-VN"
            )} ngày trong ${meta.range_days} ngày gần nhất • Trang ${meta.page}/${meta.pages || 1
                }`;
            buildPag(meta.page, meta.pages || 1);
        } catch (e) {
            console.error(e);
            els.body.innerHTML = `<tr><td class="text-danger text-center py-3" colspan="7">Lỗi tải dữ liệu</td></tr>`;
            els.sum.textContent = "—";
            els.pag.innerHTML = "";
        }
    }

    function buildPag(cur, total) {
        const maxButtons = 5;
        let start = Math.max(1, cur - Math.floor(maxButtons / 2));
        let end = start + maxButtons - 1;
        if (end > total) {
            end = total;
            start = Math.max(1, end - maxButtons + 1);
        }

        const prevDis = cur <= 1 ? " disabled" : "";
        const nextDis = cur >= total ? " disabled" : "";

        let html = `
            <li class="page-item${prevDis}"><a class="page-link" href="#" data-page="${cur - 1
            }">&laquo;</a></li>`;
        for (let p = start; p <= end; p++) {
            const act = p === cur ? " active" : "";
            html += `<li class="page-item${act}"><a class="page-link" href="#" data-page="${p}">${p}</a></li>`;
        }
        html += `
            <li class="page-item${nextDis}"><a class="page-link" href="#" data-page="${cur + 1
            }">&raquo;</a></li>`;

        els.pag.innerHTML = html;
        els.pag.querySelectorAll("a.page-link").forEach((a) => {
            a.addEventListener("click", (ev) => {
                ev.preventDefault();
                const target = parseInt(a.getAttribute("data-page"), 10);
                if (!isNaN(target)) loadCW(target);
            });
        });
    }

    els.range.addEventListener("change", () => loadCW(1));

    // chỉ load khi tab Nước sạch mở
    document.addEventListener("DOMContentLoaded", () => {
        const btn = document.querySelector("#clean-water-tab");
        const pane = document.querySelector("#clean-water");
        if (pane?.classList.contains("active")) loadCW(1);
        btn?.addEventListener("shown.bs.tab", () => loadCW(1));
    });
})();

// Handle cho api lấy lịch sử nhập liệu bể chứa
(function () {
    const els = {
        head: document.getElementById("tanks-head"),
        body: document.getElementById("tanks-body"),
        sum: document.getElementById("tanks-summary"),
        pag: document.getElementById("tanks-pagination"),
        range: document.getElementById("tanks-range"),
    };
    if (!els.head) return;

    let page = 1;

    function fmtNum(v) {
        return typeof v === "number" ? v.toLocaleString("vi-VN") : v ?? "";
    }

    async function loadTanks(pageArg = 1) {
        page = pageArg;
        const rangeDays = parseInt(els.range.value || "30", 10);
        const params = new URLSearchParams({ page, range_days: rangeDays });

        els.body.innerHTML = `<tr><td class="text-center py-3" colspan="999">Đang tải...</td></tr>`;

        try {
            const res = await fetch(
                `/api/water-tanks/history/pivot?${params.toString()}`
            );
            const data = await res.json();

            const cols = data.columns || ["date"];
            const rows = data.rows || [];
            const meta = data.meta || {
                page: 1,
                pages: 1,
                total: 0,
                range_days: rangeDays,
            };

            // header
            els.head.innerHTML = cols
                .map((c) => `<th>${c === "date" ? "Ngày" : c}</th>`)
                .join("");

            // body
            if (!rows.length) {
                els.body.innerHTML = `<tr><td class="text-center py-3" colspan="${cols.length}">Không có dữ liệu</td></tr>`;
            } else {
                els.body.innerHTML = rows
                    .map((r) => {
                        const tds = cols
                            .map((c) =>
                                c === "date"
                                    ? `<td>${r[c] || ""}</td>`
                                    : `<td>${fmtNum(r[c])}</td>`
                            )
                            .join("");
                        return `<tr>${tds}</tr>`;
                    })
                    .join("");
            }

            els.sum.textContent = `${(meta.total || 0).toLocaleString(
                "vi-VN"
            )} ngày trong ${meta.range_days} ngày gần nhất • Trang ${meta.page}/${meta.pages || 1
                }`;
            buildPag(meta.page, meta.pages || 1);
        } catch (e) {
            console.error(e);
            els.body.innerHTML = `<tr><td class="text-danger text-center py-3" colspan="999">Lỗi tải dữ liệu</td></tr>`;
            els.sum.textContent = "—";
            els.pag.innerHTML = "";
        }
    }

    function buildPag(cur, total) {
        const maxButtons = 5;
        let start = Math.max(1, cur - Math.floor(maxButtons / 2));
        let end = start + maxButtons - 1;
        if (end > total) {
            end = total;
            start = Math.max(1, end - maxButtons + 1);
        }

        const prevDis = cur <= 1 ? " disabled" : "";
        const nextDis = cur >= total ? " disabled" : "";

        let html = `
            <li class="page-item${prevDis}"><a class="page-link" href="#" data-page="${cur - 1
            }">&laquo;</a></li>`;
        for (let p = start; p <= end; p++) {
            const act = p === cur ? " active" : "";
            html += `<li class="page-item${act}"><a class="page-link" href="#" data-page="${p}">${p}</a></li>`;
        }
        html += `
            <li class="page-item${nextDis}"><a class="page-link" href="#" data-page="${cur + 1
            }">&raquo;</a></li>`;

        els.pag.innerHTML = html;
        els.pag.querySelectorAll("a.page-link").forEach((a) => {
            a.addEventListener("click", (ev) => {
                ev.preventDefault();
                const target = parseInt(a.getAttribute("data-page"), 10);
                if (!isNaN(target)) loadTanks(target);
            });
        });
    }

    els.range.addEventListener("change", () => loadTanks(1));

    // chỉ load khi tab "Bể chứa" mở
    document.addEventListener("DOMContentLoaded", () => {
        const btn = document.querySelector("#tanks-tab");
        const pane = document.querySelector("#tanks");
        if (pane?.classList.contains("active")) loadTanks(1);
        btn?.addEventListener("shown.bs.tab", () => loadTanks(1));
    });
})();

// ===== Lịch sử NƯỚC THẢI (pivot) =====
(function () {
    const els = {
        head: document.getElementById("ww-head"),
        body: document.getElementById("ww-body"),
        sum: document.getElementById("ww-summary"),
        pag: document.getElementById("ww-pagination"),
        range: document.getElementById("ww-range"),
        p1: document.getElementById("ww-p1"),
        p2: document.getElementById("ww-p2"),
        agg: document.getElementById("ww-aggregate"),
        extra: document.getElementById("ww-extra"),
    };
    if (!els.head) return;

    function fmt(v) {
        return typeof v === "number" ? v.toLocaleString("vi-VN") : v ?? "";
    }

    async function load(page = 1) {
        const range = parseInt(els.range.value || "30", 10);
        const plants = [
            els.p1.checked ? 1 : null,
            els.p2.checked ? 2 : null,
        ].filter(Boolean);
        if (!plants.length) {
            els.body.innerHTML = `<tr><td class="text-center py-3">Chọn ít nhất 1 nhà máy</td></tr>`;
            els.head.innerHTML = "<th>Ngày</th>";
            els.sum.textContent = "—";
            els.pag.innerHTML = "";
            return;
        }

        const params = new URLSearchParams({
            page,
            range_days: range,
            aggregate: String(els.agg.checked),
            include_extra: String(els.extra.checked),
            plant_numbers: plants.join(","),
        });

        els.body.innerHTML = `<tr><td class="text-center py-3" colspan="999">Đang tải...</td></tr>`;

        try {
            const res = await fetch(
                `${window.DATA_ENTRY_CONFIG.wastewaterPivotApi}?${params.toString()}`
            );
            const data = await res.json();
            const cols = data.columns || ["date"];
            const rows = data.rows || [];
            const meta = data.meta || {
                page: 1,
                pages: 1,
                total: 0,
                range_days: range,
            };

            els.head.innerHTML = cols
                .map((c) => `<th>${c === "date" ? "Ngày" : c}</th>`)
                .join("");
            if (!rows.length) {
                els.body.innerHTML = `<tr><td class="text-center py-3" colspan="${cols.length}">Không có dữ liệu</td></tr>`;
            } else {
                els.body.innerHTML = rows
                    .map((r) => {
                        const tds = cols
                            .map((c) =>
                                c === "date"
                                    ? `<td>${r[c] || ""}</td>`
                                    : `<td>${fmt(r[c])}</td>`
                            )
                            .join("");
                        return `<tr>${tds}</tr>`;
                    })
                    .join("");
            }
            els.sum.textContent = `${(meta.total || 0).toLocaleString(
                "vi-VN"
            )} ngày trong ${meta.range_days} ngày gần nhất • Trang ${meta.page}/${meta.pages || 1
                }`;
            buildPag(meta.page, meta.pages || 1, load);
        } catch (e) {
            console.error(e);
            els.body.innerHTML = `<tr><td class="text-danger text-center py-3" colspan="999">Lỗi tải dữ liệu</td></tr>`;
            els.sum.textContent = "—";
            els.pag.innerHTML = "";
        }
    }

    function buildPag(cur, total, reload) {
        const maxButtons = 5;
        let start = Math.max(1, cur - Math.floor(maxButtons / 2));
        let end = start + maxButtons - 1;
        if (end > total) {
            end = total;
            start = Math.max(1, end - maxButtons + 1);
        }
        const prevDis = cur <= 1 ? " disabled" : "";
        const nextDis = cur >= total ? " disabled" : "";
        let html = `<li class="page-item${prevDis}"><a class="page-link" href="#" data-p="${cur - 1
            }">&laquo;</a></li>`;
        for (let p = start; p <= end; p++) {
            const act = p === cur ? " active" : "";
            html += `<li class="page-item${act}"><a class="page-link" href="#" data-p="${p}">${p}</a></li>`;
        }
        html += `<li class="page-item${nextDis}"><a class="page-link" href="#" data-p="${cur + 1
            }">&raquo;</a></li>`;
        els.pag.innerHTML = html;
        els.pag.querySelectorAll("a.page-link").forEach((a) => {
            a.addEventListener("click", (e) => {
                e.preventDefault();
                const p = parseInt(a.getAttribute("data-p"), 10);
                if (!isNaN(p)) reload(p);
            });
        });
    }

    // Bind
    ["change", "click"].forEach((ev) => {
        els.range.addEventListener(ev, () => load(1));
        els.p1.addEventListener(ev, () => load(1));
        els.p2.addEventListener(ev, () => load(1));
        els.agg.addEventListener(ev, () => load(1));
        els.extra.addEventListener(ev, () => load(1));
    });
    document.addEventListener("DOMContentLoaded", () => {
        const pane = document.querySelector("#wastewater");
        const btn = document.querySelector("#wastewater-tab");
        if (pane?.classList.contains("active")) load(1);
        btn?.addEventListener("shown.bs.tab", () => load(1));
    });
})();

// ===== Lịch sử KHÁCH HÀNG (list) =====
(function () {
  const CFG = window.DATA_ENTRY_CONFIG || {};
  const sel = (CFG.selectors && CFG.selectors.customersHistory) || {};
  const els = {
    head: document.querySelector(sel.head || '#cust-head'),
    body: document.querySelector(sel.body || '#cust-body'),
    sum:  document.querySelector(sel.summary || '#cust-summary'),
    pag:  document.querySelector(sel.pagination || '#cust-pagination'),
    range:document.querySelector(sel.range || '#cust-range'),
    type: document.querySelector(sel.type || '#cust-type'),
    search:document.querySelector(sel.search || '#cust-search'),
    tabBtn: document.querySelector(sel.tab || '#customers-tab'),
    pane:  document.querySelector(sel.pane || '#customers')
  };
  if (!els.head) return;

  function fmt(v){ return (typeof v==='number') ? v.toLocaleString('vi-VN') : (v ?? ''); }

  async function load(page=1){
    const params = new URLSearchParams({
      page,
      range_days: parseInt(els.range?.value || '30', 10)
    });
    const t = (els.type?.value || '').trim();
    if (t) params.set('type', t);
    const q = (els.search?.value || '').trim();
    if (q) params.set('q', q);

    els.body.innerHTML = `<tr><td class="text-center py-3" colspan="9">Đang tải...</td></tr>`;

    try{
      const res = await fetch(`${CFG.customerHistoryApi}?${params.toString()}`);
      const data = await res.json();

      const rows = data.rows || [];
      const meta = data.meta || { page:1, pages:1, total:0, range_days: params.get('range_days') };

      if (!rows.length){
        els.body.innerHTML = `<tr><td class="text-center py-3" colspan="9">Không có dữ liệu</td></tr>`;
      } else {
        els.body.innerHTML = rows.map(r => {
          return `
            <tr>
              <td>${r.date || ''}</td>
              <td>${r.company || ''}</td>
              <td>${r.type || ''}</td>
              <td>${fmt(r.ratio)}</td>
              <td>${fmt(r.clean_1)}</td>
              <td>${fmt(r.clean_2)}</td>
              <td>${fmt(r.clean_3)}</td>
              <td>${fmt(r.wastewater)}</td>
              <td>${r.source === 'actual' ? 'Nhập tay' : 'Tính theo tỷ lệ'}</td>
            </tr>`;
        }).join('');
      }

      els.sum.textContent = `${(meta.total||0).toLocaleString('vi-VN')} bản ghi trong ${meta.range_days} ngày gần nhất • Trang ${meta.page}/${meta.pages||1}`;
      buildPag(meta.page, meta.pages || 1);
    }catch(e){
      console.error(e);
      els.body.innerHTML = `<tr><td class="text-danger text-center py-3" colspan="9">Lỗi tải dữ liệu</td></tr>`;
      els.sum.textContent = '—';
      els.pag.innerHTML = '';
    }
  }

  function buildPag(cur, total){
    const maxButtons = 5;
    let start = Math.max(1, cur - Math.floor(maxButtons/2));
    let end = start + maxButtons - 1;
    if (end > total) { end = total; start = Math.max(1, end - maxButtons + 1); }
    const prevDis = (cur <= 1) ? ' disabled' : '';
    const nextDis = (cur >= total) ? ' disabled' : '';

    let html = `<li class="page-item${prevDis}"><a class="page-link" href="#" data-p="${cur-1}">&laquo;</a></li>`;
    for (let p = start; p <= end; p++) {
      const act = (p === cur) ? ' active' : '';
      html += `<li class="page-item${act}"><a class="page-link" href="#" data-p="${p}">${p}</a></li>`;
    }
    html += `<li class="page-item${nextDis}"><a class="page-link" href="#" data-p="${cur+1}">&raquo;</a></li>`;

    els.pag.innerHTML = html;
    els.pag.querySelectorAll('a.page-link').forEach(a=>{
      a.addEventListener('click', e=>{
        e.preventDefault();
        const p = parseInt(a.getAttribute('data-p'), 10);
        if (!isNaN(p)) load(p);
      });
    });
  }

  // Khởi chạy khi mở tab Khách hàng và khi thay filter/search
  function onReady(fn){ if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',fn);} else { fn(); } }
  onReady(() => {
    if (els.pane?.classList.contains('active')) load(1);
    els.tabBtn?.addEventListener('shown.bs.tab', () => load(1));
    els.range?.addEventListener('change', () => load(1));
    els.type?.addEventListener('change', () => load(1));
    let typingTimer;
    els.search?.addEventListener('input', () => {
      clearTimeout(typingTimer);
      typingTimer = setTimeout(()=>load(1), 300); // debounce search
    });
  });
})();

// ===== POPUP Lưu =====
(function(){
  function ensureModal(id, html){
    let el = document.getElementById(id);
    if (!el){
      const wrap = document.createElement('div');
      wrap.innerHTML = html.trim();
      el = wrap.firstElementChild;
      document.body.appendChild(el);
    }
    return el;
  }

  // Confirm LẦN ĐẦU LƯU
  window.showConfirmFirstSave = function(opts){
    const html = `
    <div id="firstSaveModal" class="modal fade" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content shadow-lg">
          <div class="modal-header border-0">
            <h5 class="modal-title">
              <i class="fas fa-shield-check text-primary me-2"></i>
              Xác nhận lưu
            </h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Đóng"></button>
          </div>
          <div class="modal-body">
            <p class="mb-2 text-muted">Bạn sắp lưu dữ liệu ngày
              <b class="fs-date"></b> cho <span class="fs-entity fw-semibold"></span>.
            </p>
            <div class="bg-light rounded p-2 mb-3 small" style="max-height: 220px; overflow:auto">
              <div class="fs-items"></div>
            </div>
            <div class="alert alert-warning mb-0">
              <i class="fas fa-lock me-2"></i><b>Lưu ý:</b>
              Sau khi lưu thành công, bản ghi sẽ <u>bị khóa và không thể chỉnh sửa</u>.
            </div>
          </div>
          <div class="modal-footer border-0">
            <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Hủy</button>
            <button type="button" class="btn btn-primary btn-confirm">Tôi hiểu và muốn lưu</button>
          </div>
        </div>
      </div>
    </div>`;
    return new Promise((resolve)=>{
      const el = ensureModal('firstSaveModal', html);
      let dateText = opts?.date || '';
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateText)) {
        const [y, m, d] = dateText.split('-');
        dateText = `${d}/${m}/${y}`;
        }
        el.querySelector('.fs-date').textContent = dateText;
        el.querySelector('.fs-entity').textContent = opts?.entity || '';
        const lines = Array.isArray(opts?.lines) ? opts.lines : [];
        el.querySelector('.fs-items').innerHTML    = `<pre class="mb-0">${lines.join('\n')}</pre>`;

        const bs = new bootstrap.Modal(el, { backdrop: 'static', keyboard: false });
        const okBtn = el.querySelector('.btn-confirm');

        const onOk = () => { cleanup(); resolve(true); };
        const onHide = () => { cleanup(); resolve(false); };
        function cleanup(){
        okBtn.removeEventListener('click', onOk);
            el.removeEventListener('hidden.bs.modal', onHide);
        }
        okBtn.addEventListener('click', onOk);
        el.addEventListener('hidden.bs.modal', onHide, { once: true });
        bs.show();
    });
  };

  // Thông báo đã KHÓA (không cho sửa)
  window.showLockedInfo = function(message){
    const html = `
    <div id="lockedInfoModal" class="modal fade" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-sm modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-body text-center p-4">
            <div class="text-warning mb-2"><i class="fas fa-lock fa-2x"></i></div>
            <div class="mb-3">${message || 'Bản ghi đã bị khóa, không thể chỉnh sửa.'}</div>
            <button class="btn btn-primary w-100" data-bs-dismiss="modal">Đã hiểu</button>
          </div>
        </div>
      </div>
    </div>`;
    const el = ensureModal('lockedInfoModal', html);
    el.querySelector('.mb-3').innerHTML = message || 'Bản ghi đã bị khóa, không thể chỉnh sửa.';
    const bs = new bootstrap.Modal(el, { backdrop: 'static', keyboard: false });
    el.addEventListener('hidden.bs.modal', ()=> el.remove(), { once: true });
    bs.show();
  };

  // Chặn double-submit khi modal đang mở
  document.addEventListener('shown.bs.modal', (e)=>{
    if (e.target.id === 'firstSaveModal'){
      document.querySelectorAll('form').forEach(f => f.classList.add('pe-none'));
    }
  });
  document.addEventListener('hidden.bs.modal', (e)=>{
    if (e.target.id === 'firstSaveModal'){
      document.querySelectorAll('form').forEach(f => f.classList.remove('pe-none'));
    }
  });
})();


