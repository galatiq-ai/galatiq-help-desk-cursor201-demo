# Same contract test for every cloud: only the mock_provider line differs.
mock_provider "aws" {}

variables {
  name           = "dcbuildartifacts"
  site           = "dfw2"
  retention_days = 90
  tags           = { owner = "it-infra", ticket = "INFRA-1043", env = "sandbox" }
}

run "plans_with_contract_outputs" {
  command = plan
  assert {
    condition     = output.store_url != null
    error_message = "store_url output missing"
  }
}

run "rejects_bad_name" {
  command = plan
  variables { name = "Bad_Name!" }
  expect_failures = [var.name]
}
