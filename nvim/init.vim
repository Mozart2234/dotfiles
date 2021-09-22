" --------------------------------------------------------------------------
" BASIC CONFIGURATION 
" --------------------------------------------------------------------------

set nocompatible    " Just Vim settings
set number          " Activates number lines
set backspace=2     " Fix backspace behavior on most terminals.
set ruler           " Always show cursor position
set autoindent      " Respect indentation when starting a new line.
" set smartindent
set expandtab       " Expand tabs to spaces. Essential in Python.
set tabstop=2       " Number of spaces tab is counted for.
set shiftwidth=2    " Number of spaces to use for autoindent.
set backspace=2     " Fix backspace behavior on most terminals.

set encoding=UTF-8  " Use UTF-8 encoding 
set directory=~/.vim/swap//
set undofile
set undodir=~/.vim/undodir//

set laststatus=2
set showcmd

let mapleader = "\<space>" " Map the leader key to space

vnoremap < <gv
vnoremap > >gv

set clipboard=unnamed

" Folding
"
set foldmethod=syntax "syntax highlighting items specify folds  
set foldcolumn=1 "defines 1 col at window left, to indicate folding  
let javaScript_fold=1 "activate folding by JS syntax  
set foldlevelstart=99 "start file with all folds opened
set nofoldenable

" --------------------------------------------------------------------------
" BASIC CONFIGURATION 
" --------------------------------------------------------------------------

set hlsearch " Highlight searches by default


" --------------------------------------------------------------------------
" PERSONALIZATION 
" --------------------------------------------------------------------------

colorscheme desert

" --------------------------------------------------------------------------
" CODING CONFIGURATION 
" --------------------------------------------------------------------------

syntax on " Enable syntax highlighting
filetype plugin indent on " Enable file type based information

" --------------------------------------------------------------------------
" PERSONAL COMMANDS
" --------------------------------------------------------------------------

command! PackUpdate call minpac#update() 
command! PackClean call minpac#clean()

" --------------------------------------------------------------------------
" SPLIT CONFIGURATION 
" --------------------------------------------------------------------------

noremap <c-h> <c-w><c-h>
noremap <c-j> <c-w><c-j>
noremap <c-k> <c-w><c-k>
noremap <c-l> <c-w><c-l>

set splitbelow
set splitright

" --------------------------------------------------------------------------
" UI CONFIGURATION 
" --------------------------------------------------------------------------

packadd! dracula
set termguicolors       "enable true colors support
let g:rehash256=1
set t_Co=256
set background=dark

colorscheme dracula 

" --------------------------------------------------------------------------
" PLUGINS 
" --------------------------------------------------------------------------

packadd minpac
call minpac#init()

" --------------------------------------------------------------------------
" Utilities
" --------------------------------------------------------------------------

" Utility
call minpac#add('easymotion/vim-easymotion')
call minpac#add('tpope/vim-surround')
call minpac#add('tpope/vim-unimpaired')
call minpac#add('tpope/vim-commentary')
call minpac#add('wakatime/vim-wakatime')
call minpac#add('neoclide/coc.nvim', { 'branch': 'release' })
call minpac#add('preservim/nerdtree')
call minpac#add('junegunn/fzf')
call minpac#add('junegunn/fzf.vim')
call minpac#add('sheerun/vim-polyglot')


" Javascript 
call minpac#add('pangloss/vim-javascript')
call minpac#add('peitalin/vim-jsx-typescript')
call minpac#add('HerringtonDarkholme/yats.vim')
call minpac#add('maxmellon/vim-jsx-pretty')   " JS and JSX syntax
call minpac#add('jparise/vim-graphql')        " GraphQL syntax

"" Theming
call minpac#add('vim-airline/vim-airline')
call minpac#add('lifepillar/vim-gruvbox8')
call minpac#add('patstockwell/vim-monokai-tasty')
call minpac#add('ryanoasis/vim-devicons')
call minpac#add('dracula/vim',{'name': 'dracula'})

" Ruby
call minpac#add('vim-ruby/vim-ruby')
call minpac#add('tpope/vim-rails')
call minpac#add('thoughtbot/vim-rspec')

" Git
call minpac#add('tpope/vim-fugitive')
call minpac#add('nvim-lua/plenary.nvim')
call minpac#add('lewis6991/gitsigns.nvim')

call minpac#add('k-takata/minpac', {'type': 'opt'})
call minpac#add('tpope/vim-projectionist')
call minpac#add('mhinz/vim-grepper')

" Tmux
call minpac#add('christoomey/vim-tmux-navigator')

" --------------------------------------------------------------------------
" PLUGINS CONFIGURATION
" --------------------------------------------------------------------------

" --------------------------------------------------------------------------
" FZF 
" --------------------------------------------------------------------------
nnoremap <C-p> :<C-u>:Files<CR>

" --------------------------------------------------------------------------
" VIM-FUGITIVE 
" --------------------------------------------------------------------------

nnoremap <silent> <leader>gs :Git<CR>
noremap <silent> <leader>gd :Git diff<CR>
nnoremap <silent> <leader>gc :Git commit<CR>
nnoremap <silent> <leader>gb :Git blame<CR>
nnoremap <leader>gp :Git push<CR>
nnoremap <silent> <leader>gr :Git read<CR>
nnoremap <silent> <leader>gw :Git write<CR>
nnoremap <leader>gh :diffget //2<CR>
nnoremap <leader>gl :diffget //3<CR>

" Set list of non visible characters
set listchars=eol:⏎,tab:␉·,trail:☠,nbsp:⎵
" The command :dig displays other digraphs you can use.
nmap <leader>sl :set list!<CR>

" --------------------------------------------------------------------------
" VIM-COC 
" --------------------------------------------------------------------------

let g:coc_global_extensions = ['coc-json', 'coc-solargraph', 'coc-pairs', 'coc-snippets', 'coc-tsserver', 'coc-css', 'coc-styled-components', 'coc-prettier', 'coc-flutter', 'coc-html', 'coc-emmet', 'coc-jedi', 'coc-jest']

if isdirectory('./node_modules') && isdirectory('./node_modules/eslint')
  let g:coc_global_extensions += ['coc-eslint']
endif

" Use tab for trigger completion with charactrs ahead and navigate.
" other plugin before putting this into your config.
inoremap <silent><expr> <TAB>
      \ pumvisible() ? "\<C-n>" :
      \ <SID>check_back_space() ? "\<TAB>" :
      \ coc#refresh()
inoremap <expr><S-TAB> pumvisible() ? "\<C-p>" : "\<C-h>"

function! s:check_back_space() abort
  let col = col('.') - 1
  return !col || getline('.')[col - 1]  =~# '\s'
endfunction
"
" Use <c-space> to trigger completion.
if has('nvim')
  inoremap <silent><expr> <c-space> coc#refresh()
else
  inoremap <silent><expr> <c-@> coc#refresh()
endif

" Use <cr> to confirm completion, `<C-g>u` means break undo chain at current
" position. Coc only does snippet and additional edit on confirm.
" <cr> could be remapped by other vim plugin, try `:verbose imap <CR>`.
if exists('*complete_info')
  inoremap <expr> <cr> complete_info()["selected"] != "-1" ? "\<C-y>" : "\<C-g>u\<CR>"
else
  inoremap <expr> <cr> pumvisible() ? "\<C-y>" : "\<C-g>u\<CR>"
endif

" GoTo code navigation.
nmap <silent> gd <Plug>(coc-definition)
nmap <silent> gy <Plug>(coc-type-definition)
nmap <silent> gi <Plug>(coc-implementation)
nmap <silent> gr <Plug>(coc-references)

" Remap keys for applying codeAction to the current line.
nmap <leader>ac  <Plug>(coc-codeaction)
" Apply AutoFix to problem on the current line.
nmap <leader>qf  <Plug>(coc-fix-current)

" Use `[g` and `]g` to navigate diagnostics
" Use `:CocDiagnostics` to get all diagnostics of current buffer in location list.
nmap <silent> [g <Plug>(coc-diagnostic-prev)
nmap <silent> ]g <Plug>(coc-diagnostic-next)

" Run jest for current project
command! -nargs=0 Jest :call  CocAction('runCommand', 'jest.projectTest')

" Run jest for current file
command! -nargs=0 JestCurrent :call  CocAction('runCommand', 'jest.fileTest', ['%'])

" Run jest for current test
nnoremap <leader>te :call CocAction('runCommand', 'jest.singleTest')<CR>

" Init jest in current cwd, require global jest command exists
command! JestInit :call CocAction('runCommand', 'jest.init')

" Set list of non visible characters
set listchars=eol:?,tab:?�,trail:?,nbsp:?
" The command :dig displays other digraphs you can use.
nmap <leader>sl :set list!<CR>

" --------------------------------------------------------------------------
" NERDTREE 
" --------------------------------------------------------------------------

map <C-e> :NERDTreeToggle<CR>
" autocmd bufenter * if (winnr("$") == 1 && exists("b:NERDTree") && b:NERDTree.isTabTree()) | q | endif " Autoclose NERDTree if it's the only open window left.
let NERDTreeIgnore=['\.node_modules$']


" --------------------------------------------------------------------------
" COMMANDS PRETTIER 
" --------------------------------------------------------------------------

command! -nargs=0 Prettier :CocCommand prettier.formatFile

" --------------------------------------------------------------------------
" VIM-JSX-TYPESCRIPT 
" --------------------------------------------------------------------------

" set filetypes as typescriptreact
autocmd BufNewFile,BufRead *.tsx,*.jsx set filetype=typescriptreact
