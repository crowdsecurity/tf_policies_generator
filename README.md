
# Terraform Policies generator

This tool generates policies from a Terraform plan for Continuous Deployment using OIDC.

Related [blog post](https://www.crowdsec.net/blog/a-guide-to-continuous-deployment)

## Install

```
pip install git+https://github.com/crowdsecurity/tf_policies_generator
```

## Usage

```
terraform plan -out plan.out
terraform show -no-color -json plan.out > output.json
tf_policies_generator -f output.json
```
