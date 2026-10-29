% Font shape
\NeedsTeXFormat{LaTeX2e}[1995/12/01] 

\ProvidesClass{rbie2026}[2022/12/14, v3.0]

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax

\LoadClass[twoside,twocolumn,10pt,a4paper]{article}
\setlength{\parindent}{20pt}


% Pacote que contém o glifo do ORCID
\RequirePackage{orcidlink}

% Pacote que contém o glifo do envelope de carta
\RequirePackage{fontawesome}

% Identify the engine in use (pdftex, luatex, xetex)
\RequirePackage{iftex}
\ifpdftex % caso o engine seja o pdflatex
	\RequirePackage[T1]{fontenc}
	%\RequirePackage{lmodern}
        \usepackage{tgtermes}
	\RequirePackage[tracking=smallcaps]{microtype}
	\RequirePackage[book]{FiraSans}
     \else % caso o engine seja o xelatex ou lualatex
        \RequirePackage{fontspec}
        \setmainfont{TeX Gyre Termes}%% esse typeface eh versao livre 
	%% e gratuita do {Times New Roman} que as editoras tem mas os usuarios nao tem acesso. A familia TeX Gyre esta disponivel na distribuicao TEXLIVE que eh usada pelo OverLeaf. Pode ser que o OverLeaf tenha o Times New Roman na sua configuracao. 
	%% Ha que se investigar isso!
	\setsansfont{Roboto}
\fi

\RequirePackage{xcolor}
\RequirePackage{graphicx}

\RequirePackage{etoolbox}
\RequirePackage{amsmath,amssymb}
\RequirePackage[style]{abstract}
\RequirePackage{enumitem}
\RequirePackage[explicit]{titlesec}
\RequirePackage{caption}
\RequirePackage{fancyhdr}
\RequirePackage{hyperref} 
\RequirePackage[a4paper,top=.4in,includehead,headsep=10pt,headheight=28pt,left=.70in,textwidth=41.5pc,textheight=60pc,columnsep=18pt,footskip=18pt]{geometry}

%% Print source codes
\RequirePackage{listings}

% Minted package provides syntax highlighting
\RequirePackage{minted}
\setminted{
  fontsize=\small,
  breaklines=true,
  linenos=true,
  frame=lines,
  numbersep=5pt,
  bgcolor=gray!8
}

%% Creates the floating environment 'algorithm', similarly to figures and tables
\RequirePackage{algorithm}
% Provides the actual pseudocode commands (\State, \If, \For, % \While, \Function, etc.)
\RequirePackage{algpseudocode}

% This command renders the line numbers in light gray, so that they do not compete visually with the code
\renewcommand{\theFancyVerbLine}{%
  \textcolor{gray}{\footnotesize\arabic{FancyVerbLine}}%
}

% LaTeX 3 extensions
\RequirePackage{expl3}
\RequirePackage{xparse}

% String manipulation
\RequirePackage{xstring}
\RequirePackage{trimspaces}

\RequirePackage{babel}
\RequirePackage{iflang}

% Arithmetic expressions in \set{length,counter} & \addto{length,counter};
% commands \widthof, \heightof, \depthof, \totalheightof, \settototalheight
\RequirePackage{calc}

% Custom color definitions
    % Titles in other languages (cinza 0.30 sobre branco rende contraste de ~8:1)
    \definecolor{engtitle}{rgb}{0.30,0.30,0.30}
    \definecolor{thirdlangtitle}{rgb}{0.30,0.30,0.30}
\definecolor{orcidlogo}{rgb}{0.37,0.48,0.13}
\definecolor{unilogo}{rgb}{0.16, 0.26, 0.58}
\definecolor{maillogo}{rgb}{0.58, 0.16, 0.26}
\definecolor{darkblue}{rgb}{0.0,0.0,0.7}
% Acessibilidade: pdfdisplaydoctitle faz o leitor de tela anunciar o titulo do documento (definido em \pdftitle) em vez do nome do arquivo. O idioma do PDF (/Lang) e definido por \DocumentMetadata{lang=...} no inicio de cada main-*.tex.
\hypersetup{colorlinks, breaklinks,
            linkcolor=black, urlcolor=darkblue,
            anchorcolor=black, citecolor=black,
            pdfdisplaydoctitle=true}
\colorlet{variablecolor}{darkblue}

\ExplSyntaxOn

% We need to have at least some variant of Portuguese and of English loaded to generate the abstract/resumo.
%
% babel traditionally uses "portuguese", "brazilian", "portugues", or "brazil" to support the Portuguese language, using .ldf files. babel is also in the process of implementing a new scheme, using .ini files, based on the concept of "locales" instead of "languages". This mechanism uses the names "portuguese-portugal", "portuguese-brazil", "portuguese-pt", "portuguese-br", "portuguese", "brazilian", "pt",
% "pt-PT", and "pt-BR" (i.e., neither "portugues" nor "brazil"). To avoid compatibility problems, let's stick with "brazilian" or "portuguese" by substituting portugues and brazil if necessary.

\seq_gclear_new:N \l_tmpa_seq
\seq_gclear_new:N \l_tmpb_seq
\seq_gset_from_clist:NN \l_tmpa_seq \@classoptionslist

% First, make sure any instances of "portugues" and "brazil" are replaced by "portuguese" and "brazilian"; other options are unchanged.
\seq_map_inline:Nn \l_tmpa_seq {
  \def\@tempa{#1}
  \ifstrequal{portugues}{#1}
    {
      \ClassWarning{rbie2026}{Substituting~language~portugues~->~portuguese}
      \def\@tempa{portuguese}
    }
    {}
  \ifstrequal{brazil}{#1}
    {
      \ClassWarning{rbie2026}{Substituting~language~brazil~->~brazilian}
      \def\@tempa{brazilian}
    }
    {}
  \seq_gput_right:NV \l_tmpb_seq {\@tempa}
}

% Remove the leftmost duplicates (default is to remove the rightmost ones).
% Necessary in case the user did "portugues,portuguese", "brazil,brazilian" or some variation: When we substitute the language, we may end up with the exact same language twice, which may mess up the main language selection.
\seq_greverse:N \l_tmpb_seq
\seq_gremove_duplicates:N \l_tmpb_seq
\seq_greverse:N \l_tmpb_seq

% If the user failed to select some variation of English and Portuguese, we add them here. We also remember which ones of portuguese/brazilian, english/american/british etc. were selected.
\exp_args:Nnx \regex_extract_all:nnNTF
  {\b(ptbr|portuguese|brazilian)\b}
  {\seq_use:Nn \l_tmpb_seq {,}}
  \l_tmpa_tl
  {
    \tl_reverse:N \l_tmpa_tl
    \xdef\@SBCpt{\tl_head:N \l_tmpa_tl}
  }
  {
    \seq_gput_left:Nn \l_tmpb_seq {ptbr}
    \gdef\@SBCpt{ptbr}
  }

\exp_args:Nnx \regex_extract_all:nnNTF
  {\b(spanish)\b}
  {\seq_use:Nn \l_tmpb_seq {,}}
  \l_tmpa_tl
  {
    \tl_reverse:N \l_tmpa_tl
    \xdef\@SBCes{\tl_head:N \l_tmpa_tl}
  }
  {
    \seq_gput_left:Nn \l_tmpb_seq {spanish}
    \gdef\@SBCes{spanish}
  }

\exp_args:Nnx \regex_extract_all:nnNTF
  {\b(english|american|USenglish|canadian|british|UKenglish|australian|newzealand)\b}
  {\seq_use:Nn \l_tmpb_seq {,}}
  \l_tmpa_tl
  {
    \tl_reverse:N \l_tmpa_tl
    \xdef\@SBCen{\tl_head:N \l_tmpa_tl}
  }
  {
    \seq_put_left:Nn \l_tmpb_seq {english}
    \gdef\@SBCen{english}
  }

% Capture the document's PRIMARY language (the one given in \documentclass).
% After the auto-add of the missing languages above, the primary language is the
% LAST item of the list, so we read it from the right.
\seq_get_right:NN \l_tmpb_seq \l_tmpa_tl
\cs_gset_nopar:Npx \@SBCmain { \tl_use:N \l_tmpa_tl }

\xdef\@classoptionslist{\seq_use:Nn \l_tmpb_seq {,}}

\ExplSyntaxOff

\xdef\@classoptionslist{twoside,twocolumn,11pt,a4paper,\@classoptionslist}
\expandafter\let\csname opt@rbie2026.cls\endcsname\@classoptionslist

\renewcommand{\title}[2][]{%
  \gdef\@shorttitle{#1}
  \gdef\@title{#2}
}

\renewcommand{\author}[2][]{%
  \gdef\@shortauthor{#1}
  \gdef\@author{#2}
}

\newcommand{\affil}[1]{\par\noindent\affilfont#1\par}

\def\@shortauthor{}
\def\@shorttitle{}
\def\@jyear{}
\def\@jnum{}
\def\@jid{}
\def\@jtitle{}
\def\@engtitle{}
\def\@thirdlangtitle{}
\def\@category{}
\def\@copyrightstatement{}
\def\@issn{}
\def\@doi{}
\def\@rbielogo{RBIElogo}
\newcommand{\rbielogo}[1]{\gdef\@rbielogo{#1}}

\newcommand{\issn}[1]{\gdef\@issn{#1}}
\newcommand{\doi}[1]{\gdef\@doi{#1}}
\newcommand{\jyear}[1]{\gdef\@jyear{#1}}
\newcommand{\jid}[1]{\gdef\@jid{#1}}
\newcommand{\jtitle}[1]{\gdef\@jtitle{#1}}
\newcommand{\engtitle}[1]{\gdef\@engtitle{#1}}
\newcommand{\thirdlangtitle}[1]{\gdef\@thirdlangtitle{#1}}
\newcommand{\category}[1]{\gdef\@category{#1}}
\newcommand{\copyrightstatement}[1]{\gdef\@copyrightstatement{#1}}

\RequirePackage{environ}
\RequirePackage{cuted}
\global\let\@setmarks\relax % fallback: cuted only defines \@setmarks during the first-column pass
\NewEnviron{frontmatter}{\begin{strip}\BODY\end{strip}\saythanks}

\def\categoryfont{\fontsize{8}{12}\bfseries\selectfont\sffamily\vskip5.5pt\raggedright\mathversion{normal}}

\def\titlefont{\fontsize{18}{20}\bfseries\selectfont\sffamily\raggedright\mathversion{normal}}
\def\engtitlefont{\fontsize{14}{12}\bfseries\selectfont\sffamily\raggedright\mathversion{normal}}
\def\thirdlangtitlefont{\fontsize{14}{12}\bfseries\selectfont\sffamily\raggedright\mathversion{normal}}
\def\authorfont{\fontsize{10}{8}\selectfont\sffamily\raggedright\mathversion{normal}}
\def\affilfont{\footnotesize\raggedright\mathversion{normal}}


\def\abstractfont{\small\rightskip5.5pc}
\def\keywordfont{\small\rightskip5.5pc}
\def\mailfont{\small\rightskip5.5pc}
\def\datefont{\footnotesize\rightskip5.5pc}
\def\licensefont{\bfseries\small}

%% Section
\def\sectionfont{\fontsize{14}{14}\sffamily\bfseries\rightskip1pc plus1fill\mathversion{bold}}
\def\subsectionfont{\fontsize{12}{12}\sffamily\bfseries\rightskip1pc plus1fill\mathversion{bold}}
\def\subsubsectionfont{\sffamily\bfseries\normalsize\itshape\rightskip1pc plus1fill\mathversion{normal}}
\def\paragraphfont{\bfseries\normalsize\itshape\mathversion{normal}}%
\def\subparagraphfont{\normalsize}%
\def\subsubparagraphfont{\normalsize}%
\def\bibliofont{\small}
\def\tabnotefont{\footnotesize}

\renewcommand{\@maketitle}{%
  \vspace*{-46pt} % pulls the rule closer to the header (title page only)
  \rule{\linewidth}{.27pt}\vspace{2pt} {\categoryfont\scshape\@category\par}

  \vskip4pt
  {\titlefont\@title\par}
%  {\textit{\engtitlefont\@engtitle\par}}
  \vskip6pt
  {\engtitlefont\itshape{\@engtitle}\par}
  \vskip6pt
  {\thirdlangtitlefont\itshape{\@thirdlangtitle}\par}
  \vskip3.7pt
  \vspace{5.5pt}
  {\authorfont\@author\par}
%  \vskip1pt
}


\gdef\abstractname{}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\abstractname{}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\abstractname{}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\abstractname{}}
%\renewcommand{\abstractname}{}

\gdef\tablename{Table}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\tablename{Table}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\tablename{Tabela}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\tablename{Tabla}}
%\renewcommand{\tablename}{Tabela}

\gdef\figurename{Figure}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\figurename{Figure}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\figurename{Figura}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\figurename{Figura}}
%\renewcommand{\figurename}{Figura}

\gdef\refname{References}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\refname{References}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\refname{Refer\^encias}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\refname{Referencias}}
%\renewcommand{\refname}{Refer\^encias}

% ── Box counter and trilingual name
\newcounter{inputbox}
\renewcommand{\theinputbox}{\arabic{inputbox}}

% default value:
\gdef\inputboxname{Inputbox}

\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\inputboxname{Box}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\inputboxname{Caixa}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\inputboxname{Caja}}

% ── Ambiente 'inputbox' (contador, \theinputbox e \inputboxname já definidos acima)
\RequirePackage{tcolorbox}
\tcbuselibrary{skins,breakable}
\NewTColorBox{inputbox}{m}{
  colback          = white,
  colframe         = black,
  sharp corners,
  boxrule          = 0.05em, % igual a midrule
  coltitle         = black,
  colbacktitle     = white,
  fonttitle        = \footnotesize\bfseries,
  title            = \refstepcounter{inputbox}\inputboxname~\theinputbox.
                     {\normalfont\footnotesize #1}
}

% ── Rótulo trilíngue do ambiente 'algorithm'
\floatname{algorithm}{\algorithmname}

% default value:
\gdef\algorithmname{Algorithm}

\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\algorithmname{Algorithm}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\algorithmname{Algoritmo}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\algorithmname{Algoritmo}}

% ── Rótulo trilíngue do ambiente 'listing'
% \floatname vincula o rótulo do flutuante ao comando
% \listingname, redefinido dinamicamente conforme o idioma
% ativo do babel em cada versão do template.
\floatname{listing}{\listingname}

% default value:
\gdef\listingname{Listing}

\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\listingname{Listing}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\listingname{Listagem}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\listingname{Listado}}

\fancyhf{}
\pagestyle{fancy}
\renewcommand{\headrulewidth}{0pt}
%\fancyhead[LE,RO]{\thepage}
%\fancyhead[LO]{\itshape\@shorttitle}
%\fancyhead[RE]{\itshape\@shortauthor}
\fancyhead[L]{\footnotesize\itshape\@shorttitle}
\fancyhead[R]{\footnotesize\itshape\@shortauthor}
\fancyfoot[C]{\thepage}  % inserts page number
\fancypagestyle{plain}{%
  % \setlength{\headheight}{36.90002pt}
  \setlength{\headheight}{61.5pt}
  \addtolength{\topmargin}{-8.90002pt}
  \fancyhf{}
  \lhead{%
  \raisebox{-15pt}{\includegraphics[height=40pt]{\@rbielogo}}%
    \hspace{8pt}%
    \footnotesize
    \parbox{.6\textwidth}{%
        \vskip3pt \emph{\@jtitle}\ifdefempty{\@jid}{}%
        \ifdefempty{\@issn}{}{%
          \par \vskip3pt ISSN:\space\href{https://portal.issn.org/resource/ISSN/\@issn}{\@issn}}%
        \ifdefempty{\@doi}{}{~~$\bullet$~~doi:\space\href{https://doi.org/\@doi}{\@doi}}%
        \scriptsize \ifdefempty{\@copyrightstatement}{}{%
          \vskip3pt \faCreativeCommons~~\@copyrightstatement.\\}%
          \vskip3pt
    }
  }
  \cfoot{}
}

\renewcommand{\abstitlestyle}[1]{\textbf{#1}}
\renewcommand{\abstractnamefont}{\bfseries}
\renewcommand{\abstracttextfont}{\abstractfont}
\setlength{\absleftindent}{0pt}
\setlength{\absparindent}{0pt}
\apptocmd{\abstract}{\noindent\ignorespaces}{}{}
\appto{\endabstract}{\vskip2pt}

\newenvironment{mail}{%
  \vskip4pt\noindent\mailfont{\textcolor{blue}{\faEnvelopeO}\space}\itshape%
}{\vskip0pt}

% Acessibilidade (WCAG 2.2, 3.1.2 Idioma de partes): cada resumo e envolvido em 'otherlanguage*' para que, no PDF marcado, o leitor de tela pronuncie cada bloco no idioma correto. 'otherlanguage*' (com asterisco) troca apenas hifenizacao e o atributo de idioma, de forma LOCAL, sem acionar a maquinaria de legendas do babel no .aux (por isso eh seguro dentro de 'strip'/'frontmatter'). Os nomes \@SBCpt, \@SBCes e \@SBCen sao os idiomas babel resolvidos pela classe.
\newenvironment{abstract-pt}{%
    \vskip8pt\noindent\keywordfont{\sffamily\textbf{Resumo. }}%
    \begin{otherlanguage*}{\@SBCpt}%
}{\end{otherlanguage*}\vskip0pt}

\newenvironment{abstract-es}{%
    \vskip8pt\noindent\keywordfont{\sffamily\textbf{Resumen. }}%
    \begin{otherlanguage*}{\@SBCes}%
}{\end{otherlanguage*}\vskip0pt}

\newenvironment{abstract-en}{%
    \vskip8pt\noindent\keywordfont{\sffamily\textbf{Abstract. }}%
    \begin{otherlanguage*}{\@SBCen}%
}{\end{otherlanguage*}\vskip0pt}

\newenvironment{pchaves}{%
    \vskip2pt\noindent\keywordfont{\sffamily\textbf{Palavras-chave: }}%
}{\vskip0pt}

\newenvironment{pclaves}{%
    \vskip2pt\noindent\keywordfont{\sffamily\textbf{Palabras clave: }}%
}{\vskip0pt}

\newenvironment{keywords}{%
    \vskip2pt\noindent\keywordfont{\sffamily\textbf{Keywords: }}%
}{\vskip0pt}

\newenvironment{dates}{%
    \vskip5pt\datefont\rule{\linewidth}{.27pt}
    \vskip2pt\noindent}%
{\vskip0pt\rule{\linewidth}{.27pt}\vskip12pt}

\newenvironment{license}{%
    \noindent\licensefont{\faCreativeCommons}%
}{\vskip6pt \rule{\linewidth}{.27pt}\vskip12pt }

\captionsetup*[figure]{font=footnotesize,labelfont=bf,labelsep=period,skip=2pt}
\captionsetup*[table]{font=footnotesize,position=top,labelfont=bf,labelsep=period,skip=2pt}
\captionsetup*[listing]{font=footnotesize,labelfont=bf,labelsep=period,skip=0pt}
\captionsetup*[algorithm]{font=footnotesize,labelfont=bf,labelsep=period,skip=2pt}

\gdef\declname{Declarations}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\declname{Declarations}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\declname{Declarações complementares}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\declname{Declaraciones complementarias}}
\newenvironment{declarations}{\section*{\declname}\small}{}

\gdef\ackname{Acknowledgements}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\ackname{Acknowledgements}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\ackname{Agradecimentos}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\ackname{Agradecimientos}}
\newenvironment{acknowledgements}{\subsection*{\ackname}\small}{}

\gdef\fundingname{Funding}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\fundingname{Funding}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\fundingname{Financiamento}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\fundingname{Financiación}}
\newenvironment{funding}{\subsection*{\fundingname}\small}{}

\gdef\contributionsname{Authors' Contributions}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\contributionsname{Authors' Contributions}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\contributionsname{Contribuições dos autores}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\contributionsname{Contribuciones de los autores}}
\newenvironment{contributions}{\subsection*{\contributionsname}\small}{}

\gdef\interestsname{Competing interests}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\interestsname{Competing interests}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\interestsname{Conflitos de interesse}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\interestsname{Conflictos de intereses}}
\newenvironment{interests}{\subsection*{\interestsname}\small}{}

\gdef\materialsname{Availability of data and materials}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\materialsname{Availability of data and materials}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\materialsname{Disponibilidade de dados e materiais}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\materialsname{Disponibilidad de datos y materiales}}
\newenvironment{materials}{\subsection*{\materialsname}\small}{}

\gdef\iausagename{Artificial Intelligence (AI) Usage Declaration}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\iausagename{Artificial intelligence (AI) usage declaration}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\iausagename{Declaração de utilização de inteligência artificial (IA)}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\iausagename{Declaración sobre el uso de la inteligencia artificial (IA)}}
\newenvironment{aiusagedeclaration}{\subsection*{\iausagename}\small}{}

\gdef\furthername{Further relevant information}
\expandafter\addto\csname captions\@SBCen\endcsname{\gdef\furthername{Further relevant information}}
\expandafter\addto\csname captions\@SBCpt\endcsname{\gdef\furthername{Outras informações relevantes}}
\expandafter\addto\csname captions\@SBCes\endcsname{\gdef\furthername{Otra información relevante}}
\newenvironment{furtherinformation}{\subsection*{\furthername}\small}{}

% Apply the automatic field names (Table/Tabela/Tabla, Figure/Figura, References,
% and all the declaration headings) of the document's PRIMARY language.
% We execute the caption hook directly instead of using \selectlanguage, to avoid
% babel's .aux caption-list machinery, which references caption names (\chaptername,
% \bibname, etc.) that this article-based class does not define.
%
% To restrict this to Spanish only (leaving the PT and EN templates exactly as they
% render now), replace the body of \AtBeginDocument below with:
%     \def\@tempSBC{spanish}%
%     \ifx\@SBCmain\@tempSBC \captionsspanish \fi
\AtBeginDocument{%
  \ifcsname captions\@SBCmain\endcsname
    \csname captions\@SBCmain\endcsname
  \fi
}

\titleformat{\section}
  {\sectionfont}
  {\thesection}
  {0.5em}
  {{#1}}

\titleformat{\subsection}
  {\subsectionfont}
  {\thesubsection}
  {0.5em}
  {#1}

\titleformat{\subsubsection}
  {\subsubsectionfont}
  {\thesubsubsection}
  {0.5em}
  {#1}

\titleformat{\paragraph}[runin]
  {\paragraphfont}
  {\theparagraph}
  {0.5em}
  {#1}
  
\titlespacing*{\section}{0pt}{10pt}{4pt}
\titlespacing*{\subsection}{0pt}{8pt}{1pt}
\titlespacing*{\subsubsection}{0pt}{7pt}{1pt}
\titlespacing*{\paragraph}{0pt}{6pt}{.5em}

\apptocmd{\quotation}{\setlength{\parindent}{0pt}%
\noindent\ignorespaces}{}{}
\patchcmd{\quotation}{\rightmargin\leftmargin}{\rightmargin0pt}{}{}
\setlist{noitemsep}
\newlist{unnumlist}{itemize}{1}
\setlist[unnumlist]{label={},leftmargin=2em,itemindent=-1em}

\def\x{@{\extracolsep{\fill}}}

\newcommand{\tabnote}[1]{\par\vskip1pt{\raggedright\tabnotefont #1\par}}


% Bibliography configuration (natbib).
% \bibsep controls vertical spacing between references in the reference list.
% \setcitestyle{square} enforces brackets [ ] in in-text citations, per RBIE editorial style (APA 7th).
\RequirePackage{natbib}
\setlength{\bibsep}{0.3mm}
\setcitestyle{square}

\addtolength{\textfloatsep}{-0.0cm}
\setlength\textfloatsep{0.2cm}

\endinput
