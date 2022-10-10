local function map(mode, lhs, rhs, opts)
  local options = { noremap = true }
  if opts then
    options = vim.tbl_extend("force", options, opts)
  end
  vim.api.nvim_set_keymap(mode, lhs, rhs, options)
end

-- Update Plugins
map("n", "<Leader>u", ":PackerSync<CR>")

--After searching, pressing escape stops the highlight
map("n", "<esc>", ":noh<cr><esc>", { silent = true })

-- Better indent
map("v", "<", "<gv", { silent = true })
map("v", ">", ">gv", { silent = true })

-- Switch buffer
map("n", "<S-h>", ":bprevious<CR>", { silent = true })
map("n", "<S-l>", ":bnext<CR>", { silent = true })

-- Move selected line / block of text in visual mode
map("x", "K", ":move '<-2<CR>gv-gv", { silent = true })
map("x", "J", ":move '>+1<CR>gv-gv", { silent = true })

-- Resizing panes
map("n", "<Left>", ":vertical resize +1<CR>", { silent = true })
map("n", "<Right>", ":vertical resize -1<CR>", { silent = true })
map("n", "<Up>", ":resize -1<CR>", { silent = true })
map("n", "<Down>", ":resize +1<CR>", { silent = true })

-- Nvim Tree
map("n", "<C-n>", ":NvimTreeToggle<CR>", { silent = true })
map("n", "<leader>u", ":NvimTreeFindFile<CR>", { silent = true })
