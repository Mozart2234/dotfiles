vim.cmd[[colorscheme catppuccin]]
local catppuccin = require("catppuccin")

catppuccin.setup({
  transparent_background = false,
  integrations = {
    nvimtree = {
      enabled = true,
      show_root = false, -- makes the root folder not transparent
    }
  }
})
