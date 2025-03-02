<div align="center">

# Payments Processor for ERPNext

A powerful payments automation extension for ERPNext that streamlines payment operations and provides financial insights.

<br>
</div>

## ✨ Features

*Automate and optimize payment workflows*

- **Smart Due Date Calculation** Auto-computes payment deadlines considering terms, early-payment discounts, and grace periods.

- **Bulk Payment Engine** Generate bulk payment entries for multiple invoices in a single click.

- **Automation** Schedule payments, automate reminders, and customize payment workflows.

## 🛠️ Installation

### Prerequisites

ERPNext Version-15 or above

### Frappe Cloud

Sign up for a [Frappe Cloud](https://frappecloud.com/dashboard/signup?referrer=99df7a8f) free trial, create a new site with Frappe Version-15 or above, and install ERPNext and Payments Processor from the Apps.

### Docker

Use [this guide](https://github.com/frappe/frappe_docker/blob/main/docs/custom-apps.md) to deploy Payments Processor by building your custom image.

<details>
<summary>Sample Apps JSON</summary>

```shell
export APPS_JSON='[
  {
    "url": "https://github.com/frappe/erpnext",
    "branch": "version-15"
  },
  {
    "url": "https://github.com/resilient-tech/payments-processor",
    "branch": "version-15"
  }
]'

export APPS_JSON_BASE64=$(echo ${APPS_JSON} | base64 -w 0)
```

</details>

### Manual

Once you've [set up a Frappe site](https://frappeframework.com/docs/v14/user/en/installation/), install app by executing the following commands:

<details>
<summary>Commands</summary>

Download the App using the Bench CLI

```sh
bench get-app https://github.com/resilient-tech/payments-processor.git --branch version-15
```

Install the App on your site

```sh
bench --site [site name] install-app payments_processor
```

</details>

## 📚 Documentation

- [Setup Guide](https://github.com/resilient-tech/payments-processor/blob/version-15/docs/1_setup_guide.md)
- [Reports](<https://github.com/resilient-tech/payments-processor/blob/version-15/docs/2_reports.md>)
- [Customization Guide](https://github.com/resilient-tech/payments-processor/blob/version-15/docs/3_customization_guide.md)

## 🤝 Contributing

- [Issue Guidelines](https://github.com/frappe/erpnext/wiki/Issue-Guidelines)
- [Pull Request Requirements](https://github.com/frappe/erpnext/wiki/Contribution-Guidelines)

## 📜 License

[GNU General Public License (v3)](https://github.com/resilient-tech/payments-processor/blob/version-15/license.txt)
