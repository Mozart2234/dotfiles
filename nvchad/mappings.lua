local M = {}

M.tmuxnavigator = {
 n = {
   ["<C-h>"] = { "<cmd> :lua require'nvim-tmux-navigation'.NvimTmuxNavigateLeft() <CR>", "Move Left Tmux"},
   ["<C-j>"] = { "<cmd> :lua require'nvim-tmux-navigation'.NvimTmuxNavigateDown() <CR>", "Move Down Tmux"},
   ["<C-k>"] = { "<cmd> :lua require'nvim-tmux-navigation'.NvimTmuxNavigateUp() <CR>", "Move Up Tmux"},
   ["<C-l>"] = { "<cmd> :lua require'nvim-tmux-navigation'.NvimTmuxNavigateRight() <CR>", "Move Right Tmux"}
 }
}

return M
