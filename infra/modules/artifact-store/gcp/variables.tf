# Shared interface: identical in aws/, gcp/, azure/.
variable "name" {
  type        = string
  description = "Store name, lowercase letters and digits (3-24 chars, Azure limit)."
  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.name))
    error_message = "name must be 3-24 lowercase letters/digits."
  }
}
variable "site" {
  type        = string
  description = "Data center site code, e.g. dfw2."
}
variable "retention_days" {
  type        = number
  description = "Days to keep objects before deletion."
  default     = 90
}
variable "tags" {
  type        = map(string)
  description = "Must include owner, ticket, env."
}
