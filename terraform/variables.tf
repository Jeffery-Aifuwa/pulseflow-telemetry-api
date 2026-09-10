variable "resource_group_name" {
  description = "Name of the Azure Resource Group"
  type        = string
  default     = "pulseflow-rg"
}

variable "location" {
  description = "Azure region to deploy resources in"
  type        = string
  default     = "eastus"
}

variable "cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
  default     = "pulseflow-aks"
}

variable "acr_name" {
  description = "Globally unique name for Azure Container Registry (alphanumeric only)"
  type        = string
  default     = "pulseflowreg001" # Must be globally unique, letters and numbers only!
}