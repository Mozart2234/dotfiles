local M = {}

function M.setup()
  require("bufferline").setup {
    options = {
      numbers = "none",
      diagnostics = "nvim_lsp",
      separator_style = {" ", " "},
      show_tab_indicators = true,
      show_buffer_close_icons = true,
      show_close_icon = true,
    },
  }
end

return M
