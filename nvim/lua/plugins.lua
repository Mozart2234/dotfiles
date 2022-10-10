local M = {}

function M.setup()
  -- Indicate first time installation
  local packer_bootstrap = false

  -- Check if packer.nvim is installed
  -- Run PackerCompile if there are changes in this file
  local function packer_init()
    local fn = vim.fn
    local install_path = fn.stdpath "data" .. "/site/pack/packer/start/packer.nvim"
    if fn.empty(fn.glob(install_path)) > 0 then
      packer_bootstrap = fn.system {
        "git",
        "clone",
        "--depth",
        "1",
        "https://github.com/wbthomason/packer.nvim",
        install_path,
      }
      vim.cmd [[packadd packer.nvim]]
    end
    vim.cmd "autocmd BufWritePost plugins.lua source <afile> | PackerCompile"
  end

  -- Plugins
  local function plugins(use)
    use { "wbthomason/packer.nvim" }

    -- Ffz
    use { 'ibhagwan/fzf-lua',
      -- optional for icon support
      requires = { 'kyazdani42/nvim-web-devicons', opts = true }
    }

    -- Colorscheme
    use {
      "folke/tokyonight.nvim",
      config = function()
        vim.cmd "colorscheme tokyonight"
      end,
    }

    -- WhichKey
    use {
       "folke/which-key.nvim",
       config = function()
	 require("config.whichkey").setup()
       end,
    }

    -- Better icons
    use {
      "kyazdani42/nvim-web-devicons",
      module = "nvim-web-devicons",
      config = function()
        require("nvim-web-devicons").setup { default = true }
      end,
    }
    
    -- Lualine
    use {
      "nvim-lualine/lualine.nvim",
      event = "VimEnter",
      config = function()
	require("config.lualine").setup()
      end,
      requires = { "nvim-web-devicons", opt = true },
    }

    -- NvimTree
    use {
     "kyazdani42/nvim-tree.lua",
     requires = {
       "kyazdani42/nvim-web-devicons",
     },
     cmd = { "NvimTreeToggle", "NvimTreeClose" },
     config = function()
       require("config.nvimtree").setup()
     end,
    }

    use {
      'akinsho/bufferline.nvim', 
      tag = "v2.*", 
      requires = 'kyazdani42/nvim-web-devicons',
      config = function()
	require("config.bufferline").setup()
      end
    }

    -- using packer.nvim
    if packer_bootstrap then
      print "Restart Neovim required after installation!"
      require("packer").sync()
    end
  end

  packer_init()

  local packer = require "packer"

  packer.init()
  packer.startup(plugins)
end

return M
