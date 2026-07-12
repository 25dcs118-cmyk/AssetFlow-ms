/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AssetflowDashboard extends Component {
    static template = "assetflow.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            available: 0,
            allocated: 0,
            maintenance: 0,
            bookings: 0,
            transfers: 0,
            overdue: 0,
        });
        onWillStart(() => this.loadKpis());
    }

    async loadKpis() {
        const [available, allocated, maintenance, bookings, transfers, overdue] = await Promise.all([
            this.orm.searchCount("asset.asset", [["state", "=", "available"]]),
            this.orm.searchCount("asset.asset", [["state", "=", "allocated"]]),
            this.orm.searchCount("asset.maintenance.request", [["state", "in", ["approved", "in_progress"]]]),
            this.orm.searchCount("resource.booking", [["state", "in", ["upcoming", "ongoing"]]]),
            this.orm.searchCount("asset.transfer", [["state", "=", "requested"]]),
            this.orm.searchCount("asset.allocation", [["is_overdue", "=", true]]),
        ]);
        Object.assign(this.state, { available, allocated, maintenance, bookings, transfers, overdue });
    }

    openAssets(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Assets",
            res_model: "asset.asset",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    openMaintenance(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Maintenance Requests",
            res_model: "asset.maintenance.request",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    openBookings(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Bookings",
            res_model: "resource.booking",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    openTransfers(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Transfer Requests",
            res_model: "asset.transfer",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    openAllocations(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Allocations",
            res_model: "asset.allocation",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    quickCreate(resModel, name) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: resModel,
            views: [[false, "form"]],
            target: "new",
        });
    }

    onCardPointerMove(ev) {
        const card = ev.currentTarget;
        const rect = card.getBoundingClientRect();
        card.style.setProperty("--spot-x", `${ev.clientX - rect.left}px`);
        card.style.setProperty("--spot-y", `${ev.clientY - rect.top}px`);
    }
}

registry.category("actions").add("assetflow_dashboard", AssetflowDashboard);
