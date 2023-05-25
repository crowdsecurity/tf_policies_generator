
# Terraform Policies generator

This tool is used to generate policies from a Terraform plan.

## Install

```
pip install git+https://github.com/crowdsecurity/terraform-policies_generator
```

## Usage

```
terraform plan -out plan.out
terraform show -no-color -json plan.out > output.json
policies_generator -f output.json
```