local M = {}

M.plugins = {
  options = {
    lspconfig = {
      setup_lspconf = "custom.plugins.lspconfig",
    },
  },

  user = require "custom.plugins"
}

M.mappings = require "custom.mappings"

return M
