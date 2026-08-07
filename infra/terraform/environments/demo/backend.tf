terraform {
  backend "s3" {
    key          = "environments/demo/terraform.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}
