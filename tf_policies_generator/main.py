import json
import argparse
import re

# init arguments
parser = argparse.ArgumentParser()
parser.add_argument("--file", "-f", help="Terraform plan file", required=True)
parser.add_argument("--aws-account", default="${local.env.aws_account}", help="AWS account id (default: ${local.env.aws_account})")
parser.add_argument("--aws-region", default="${local.env.aws_region}", help="AWS region (default: ${local.env.aws_region})")
parser.add_argument("--output", "-o", default="policies.tf.json", help="Output file (default: policies.json)")
args = parser.parse_args()


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

class Arn(object):
    def __init__(self, partition, service, region, account_id, resource_type, resource, ignore):
        self.partition = partition
        self.service = service
        self.region = region
        self.account_id = account_id
        self.resource_type = resource_type
        self.resource = resource
        self.resource_type_ignore = ignore
    
    @classmethod
    def from_string(self, arn):
        """
        Parse an ARN string and return an Arn object
        """
        match = re.match(r"^arn:(?P<Partition>[^:\n]*):(?P<Service>[^:\n]*):(?P<Region>[^:\n]*):(?P<AccountID>[^:\n]*):(?P<Ignore>(?P<ResourceType>[^:\/\n]*)[:\/])?(?P<Resource>.*)$", arn)
        if match:
            arn = Arn(
                partition=match.group("Partition"),
                service=match.group("Service"),
                region=match.group("Region"),
                account_id=match.group("AccountID"),
                resource_type=match.group("ResourceType"),
                ignore=match.group("Ignore"),
                resource=match.group("Resource"),
            )
            if arn.resource_type == "task-definition":
                if ":" in arn.resource:
                    arn.resource = arn.resource.split(":")[0]
            return arn
        else:
            raise Exception(f"Invalid ARN: {arn}")
    
    def __str__(self):
        if self.resource_type_ignore is None:
            return f"arn:{self.partition}:{self.service}:{self.region}:{self.account_id}:{self.resource}"
        return f"arn:{self.partition}:{self.service}:{self.region}:{self.account_id}:{self.resource_type_ignore}{self.resource}"


class PoliciesGenerator:
    def __init__(self, plan, aws_account, aws_region):
        self.plan = plan
        self.aws_account = aws_account
        self.aws_region = aws_region
        self.policies = []
        self.resources = {}
        self.ignore_read_services = ["ssm"]
        self._check_format_version()
        self._init_types_from_plan()
    
    def _check_format_version(self):
        """
        Check the terraform plan format version
        """
        if self.plan["format_version"] not in ["1.1", "1.0", "0.2"]:
            raise Exception("Invalid terraform plan format version")

    def _extract_resources(self, resources):
        """
        Extract the resources from the terraform plan
        """
        for resource in resources:
            arn = None
            if "arn" in resource["values"]:
                arn = Arn.from_string(resource["values"]["arn"])

            if "type" in resource and resource["type"] == "aws_ecs_service":
                arn = Arn.from_string(resource["values"]["id"])
                
            if arn is not None:
                if arn.service not in self.resources:
                    self.resources[arn.service] = set()

                if arn.region != "":
                    arn.region = args.aws_region
                if arn.account_id != "":
                    arn.account_id = args.aws_account

                self.resources[arn.service].add(arn.__str__())
        return
    
    def _init_types_from_plan(self):
        """
        Init the resources types from the terraform plan (root module and child modules)
        """
        self._extract_resources(self.plan["planned_values"]["root_module"]["resources"])
        for module in self.plan["planned_values"]["root_module"]["child_modules"]:
            self._extract_resources(module["resources"])
        
        self._extract_resources(self.plan["prior_state"]["values"]["root_module"]["resources"])
        for module in self.plan["prior_state"]["values"]["root_module"]["child_modules"]:
            self._extract_resources(module["resources"])

    def generate_policies(self):
        """
        Generate the policies
        """
        for service, arn_list in self.resources.items():
            read_resources = ["*"]
            if service in self.ignore_read_services:
                read_resources = arn_list
            read_policy = {
                "effect": "Allow",
                "actions": [
                    f"{service}:Describe*",
                    f"{service}:List*",
                    f"{service}:Get*",
                    f"{service}:Read*",
                ],
                "resources": read_resources,
            }
            write_policy = {
                "effect": "Allow",
                "actions": [
                    f"{service}:*",
                ],
                "resources": arn_list,
            }
            self.policies.append(read_policy)
            self.policies.append(write_policy)
            if service == "ecs":
                self.policies.append({
                    "effect": "Allow",
                    "actions": [
                        f"{service}:RegisterTaskDefinition",
                        f"{service}:DeregisterTaskDefinition",
                    ],
                    "resources": ["*"],
                })
            if service == "logs":
                self.policies.append({
                    "effect": "Allow",
                    "actions": [
                        f"{service}:TagLogGroup",
                        f"{service}:UntagLogGroup",
                    ],
                    "resources": [x + ":log-stream:*" for x in  arn_list],
                })
    
    def write_policies(self, file=args.output):
        """
        Write the policies to a file
        """
        policies_document = {
            "data": {
                "aws_iam_policy_document": {
                    "policies": {
                        "statement": self.policies,
                    },
                },
            },
        }
        with open(file, "w") as f:
            json.dump(policies_document, f, indent=4, cls=SetEncoder)

def main():
    # Generate policies
    with open(args.file) as f:
        try:
            plan = json.load(f)
        except json.decoder.JSONDecodeError:
            print("Invalid JSON file")
            exit(1)
    policies_generator = PoliciesGenerator(plan, args.aws_account, args.aws_region)
    policies_generator.generate_policies()
    policies_generator.write_policies()
    print(f"Policies generated in {args.output}")

if __name__ == "__main__":
    main()
