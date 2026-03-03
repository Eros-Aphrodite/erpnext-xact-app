### Erpnext Xact Qfinishes App

This app is designed to fully implement the functionality of XACT (Buildxact-style) in ERPNext.

### Goals

- Provide a **Buildxact-style construction workflow** inside ERPNext for quoting and job costing
- Standardize estimating using **Cost Codes** and reusable **Assemblies** (template packs)
- Turn estimates into standard ERPNext documents:
  - **Construction Estimate → Quotation**
  - Variations / change orders → **Sales Order**
- Support ongoing project changes with **Variations** and traceable change order creation
- Keep estimation structure consistent across teams (sections, cost codes, quantities, rates, margins/allowances)

### Construction module (Buildxact-style)

- **Cost Code** – Trade / cost code masters for estimates and job costing.
- **Assembly Template** – Reusable packs of materials (and labour) with qty-per-unit; expand into estimate lines.
- **Construction Estimate** – Takeoff with sections, cost codes, quantities, rates. **Create Quotation** builds an ERPNext Quotation from selected lines.
- **Variation** – Change orders: delta lines linked to Project/Quotation/Sales Order; **Create Change Order** creates a Sales Order.
- **Construction Pricing Rule** – Margin % and allowance % by cost code / trade (for future rate building).

Workflow: **Estimate** → Create **Quotation** → (convert to **Sales Order** in ERPNext) → **Variation** → Create **Change Order** (Sales Order). Use **Cost Code** and **Assembly Template** on estimates and variations.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench --site YOUR_SITE install-app erpnext_xact_qfinishes_app
```

If the app is already in `apps/` (e.g. you created it with `bench new-app`), ensure **bench start** (or your Redis/server services) is running, then:

```bash
bench --site YOUR_SITE install-app erpnext_xact_qfinishes_app
# If you see "Duplicate entry" for Module Def, run migrate instead:
bench --site YOUR_SITE migrate
```

Then open the **Construction** workspace from the Desk.

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/erpnext_xact_qfinishes_app
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit
