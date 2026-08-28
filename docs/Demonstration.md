{\rtf1\ansi\ansicpg1252\cocoartf2870
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;\f1\froman\fcharset0 Times-Roman;\f2\froman\fcharset0 Times-Bold;
\f3\froman\fcharset0 TimesNewRomanPSMT;\f4\fmodern\fcharset0 Courier-Bold;\f5\froman\fcharset0 TimesNewRomanPS-BoldMT;
\f6\fmodern\fcharset0 Courier;\f7\froman\fcharset0 Times-Italic;}
{\colortbl;\red255\green255\blue255;\red0\green0\blue0;\red109\green109\blue109;}
{\*\expandedcolortbl;;\cssrgb\c0\c0\c0;\cssrgb\c50196\c50196\c50196;}
{\*\listtable{\list\listtemplateid1\listhybrid{\listlevel\levelnfc0\levelnfcn0\leveljc0\leveljcn0\levelfollow0\levelstartat1\levelspace360\levelindent0{\*\levelmarker \{decimal\}}{\leveltext\leveltemplateid1\'01\'00;}{\levelnumbers\'01;}\fi-360\li720\lin720 }{\listname ;}\listid1}
{\list\listtemplateid2\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat0\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid101\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid2}
{\list\listtemplateid3\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat0\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid201\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid3}
{\list\listtemplateid4\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat0\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid301\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid4}
{\list\listtemplateid5\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat0\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid401\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid5}
{\list\listtemplateid6\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat0\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid501\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid6}
{\list\listtemplateid7\listhybrid{\listlevel\levelnfc23\levelnfcn23\leveljc0\leveljcn0\levelfollow0\levelstartat0\levelspace360\levelindent0{\*\levelmarker \{disc\}}{\leveltext\leveltemplateid601\'01\uc0\u8226 ;}{\levelnumbers;}\fi-360\li720\lin720 }{\listname ;}\listid7}}
{\*\listoverridetable{\listoverride\listid1\listoverridecount0\ls1}{\listoverride\listid2\listoverridecount0\ls2}{\listoverride\listid3\listoverridecount0\ls3}{\listoverride\listid4\listoverridecount0\ls4}{\listoverride\listid5\listoverridecount0\ls5}{\listoverride\listid6\listoverridecount0\ls6}{\listoverride\listid7\listoverridecount0\ls7}}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 \
Demonstration durchgef\'fchrt am CrewAI Beispiel email_auto_responder_flow mit einem simulierten Nutzer. Extra CrewAI um keinen eigenen workflow zu simulieren.\
\
\
\
\
\
\pard\pardeftab720\partightenfactor0

\f1 \cf0 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 \
\
\
\
\pard\pardeftab720\sa240\partightenfactor0
\cf0 /tadf okay letzt start in english\
\pard\pardeftab720\partightenfactor0
\cf0 \
\
\pard\pardeftab720\sa240\partightenfactor0
\cf0 Let's get started with TADF.\
First question, to figure out how we scope this:\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 SQ0 \'97 Is this one task, several separate ones, or a whole system you want routed?
\f1\b0 \
This determines whether we go straight into the task loop, run several tasks back-to-back, or first build and confirm a task list for a whole system.\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\sa240\partightenfactor0
\cf0 F: Is this one task, several separate tasks, or a whole system you want routed? A: A whole system\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\sa240\partightenfactor0
\cf0 Good \'97 whole-system mode. That means I'll first build a task list with independently testable outcomes, you confirm/correct it, and then we route each task one by one through the gates.\
Before that, two quick context questions:\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 SQ1 \'97 What should the system achieve, and why is it being considered now?
\f1\b0 \uc0\u8232 (This frames the system objective \'97 it's not itself a task, just context for identifying the task list.)\
The system should continuously monitor a Gmail inbox, identify new emails that require action, gather any context needed to respond, and create accurate, personalized draft replies for human review. It is being considered now because recurring inbox triage and first-draft preparation consume significant time, while the final decision to review and send each response should remain with the user.\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\sa240\partightenfactor0
\cf0 Got it. That gives us the objective: continuous inbox monitoring 
\f3 \uc0\u8594 
\f1  triage 
\f3 \uc0\u8594 
\f1  context gathering 
\f3 \uc0\u8594 
\f1  draft generation, with human-in-the-loop on send.\
Two more context questions, quickly:\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 SQ2 \'97 Is this a one-off or recurring system, and roughly how often will it run?
\f1\b0 \uc0\u8232 
\f2\b SQ3 \'97 Is this a proof of concept or a production system?
\f1\b0 \
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\sa240\partightenfactor0
\cf0 F: Is this a one-off or recurring system, and roughly how often will it run? A: Recurring \'97 continuous/near-real-time\
F: Is this a proof of concept or a production system? A: Production\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\sa240\partightenfactor0
\cf0 Recurring, continuous, production system \'97 that raises the bar on things like traceability and safe failure later, but that's for the profile stage.\
Now let's identify the task list. Based on your objective, I'd propose splitting the system into three independently testable tasks:\
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls1\ilvl0
\f2\b \cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	1	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Triage
\f1\b0  \'97 for each new inbox email, decide whether it requires a response/action (and possibly categorize type/priority).\
\ls1\ilvl0
\f2\b \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	2	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Context gathering
\f1\b0  \'97 for an email flagged as action-required, retrieve the information needed to respond (thread history, related records/documents, sender context).\
\ls1\ilvl0
\f2\b \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	3	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Draft generation
\f1\b0  \'97 compose a personalized reply draft from the gathered context, for human review.\
\pard\pardeftab720\sa240\partightenfactor0
\cf0 Detection of "new email arrived" itself I'd treat as a trigger/orchestration concern, not a task with its own LLM-dependent responsibility \'97 so it stays outside TADF's scope per the framework's rules (sequencing/triggers aren't a TADF output).\
Does this task list match what you have in mind, or would you split/merge/rename anything?\
Yes that sounds fine\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\sa240\partightenfactor0
\cf0 Good \'97 three tasks confirmed: 
\f2\b Triage
\f1\b0 , 
\f2\b Context gathering
\f1\b0 , 
\f2\b Draft generation
\f1\b0 . We'll route each one through the gates in turn, starting with Triage.\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 Task 1 of 3: Triage
\f1\b0 \

\f2\b TQ0 \'97 Describe this task in your own words. What is the goal, and how would it run, step by step?
\f1\b0 \
Tell me roughly: what counts as "requires action," what inputs the task sees (subject/body/sender/thread?), and what it outputs (a flag? a category? both?).\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\sa240\partightenfactor0
\cf0 Confirmed: 
\f2\b P1 = 3, P2 = M, P3 = M.
\f1\b0 \
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 P4 \'97 Efficiency
\f1\b0 \uc0\u8232 How important are operating cost/latency for Draft verification? (0\'963, M not permitted.) Any hard ceiling?\

\f2\b P5 \'97 Robustness to messy input
\f1\b0 \uc0\u8232 How important is robustness to messy/inconsistent input (informal drafts, inconsistent evidence formatting)? (M permitted)\

\f2\b P6 \'97 Evolvability
\f1\b0 \uc0\u8232 How important is evolvability \'97 will the verification rubric or policy rules keep changing? (0\'963, M not permitted)\
\pard\pardeftab720\partightenfactor0
\cf0 \
\pard\pardeftab720\sa240\partightenfactor0
\cf0 F: P4 Efficiency: how important are operating cost/latency for Draft verification? A: 2 - important\
F: P5 Messy input: how important is robustness to messy/inconsistent input? A: 3 - critical\
F: P6 Evolvability: how likely is the verification rubric or policy rules to keep changing? A: 2 - important\
\pard\pardeftab720\partightenfactor0
\cf0 \
\
\pard\pardeftab720\sa298\partightenfactor0

\f2\b\fs36 \cf0 Verdict \'97 Task 3b: Draft Verification\
\pard\pardeftab720\sa240\partightenfactor0

\fs24 \cf0 Build this as a workflow using the verification build form: evaluate each of the five rubric criteria separately against the draft and evidence package, then aggregate the final status (
\f4\fs26 pass
\f2\fs24  / 
\f4\fs26 revision_required
\f2\fs24  / 
\f4\fs26 manual_review
\f2\fs24 ) deterministically \'97 with the claim-to-evidence mapping built via a per-item map (each claim its own bound check) rather than one combined judgment call.
\f1\b0  The decisive reason: your mandatory safe-failure requirement (P2) excludes the agent outright \'97 its measured failure direction here is uncontrolled and mostly silent, which is exactly the risk you're guarding against as the last automated check before human review.\
\pard\pardeftab720\sa280\partightenfactor0

\f2\b\fs28 \cf0 1. Gate record\
\pard\pardeftab720\sa240\partightenfactor0

\f1\b0\fs24 \cf0 No gate fired. G1 does not fire (semantic judgment needed for claim-matching and tone/policy checks). G2 does not fire (one coherent verdict). 
\f2\b G3 does not fire \'97 confirmed exception:
\f1\b0  this is a checking task, not a producing task, so the "6+ simultaneous constraints" condition doesn't apply regardless of the five-criterion count. G4 does not fire (no tool use, fixed input). G5 does not fire (no retrieval). 
\f3 \uc0\u8594 
\f1  Comparative route.\
\pard\pardeftab720\sa280\partightenfactor0

\f2\b\fs28 \cf0 2. Fit and profile record\

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrt\brdrnil \trbrdrl\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\qc\partightenfactor0

\fs24 \cf0 Criterion\cell 
\pard\intbl\itap1\pardeftab720\qc\partightenfactor0
\cf0 Applies\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 Weight\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 Workflow cap.\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 Agent cap.\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 Workflow contrib.\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 Agent contrib.\cell \row

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrl\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\partightenfactor0

\f1\b0 \cf0 T1 Rule application\cell 
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 No\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 \'97\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 \'97\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 \'97\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 0\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 0\cell \row

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrl\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 T2 Multi-item extraction\cell 
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 Yes\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 2\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 6\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 9\cell \row

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrl\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 T3 Retrieval success\cell 
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 No\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 \'97\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 \'97\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 \'97\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 0\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 0\cell \row

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrl\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 P1 Traceability\cell 
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 Yes\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 2\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 9\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 6\cell \row

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrl\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 P2 Safe failure\cell 
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 Yes\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 M\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 1\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 9\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0

\f2\b \cf0 excluded by M
\f1\b0 \cell \row

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrl\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 P3 Schema guarantee\cell 
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 Yes\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 M\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 2\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 9\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 6\cell \row

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrl\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 P4 Efficiency\cell 
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 Yes\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 2\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 2*\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 6\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 6*\cell \row

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrl\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 P5 Messy input\cell 
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 Yes\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 2\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 6\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 9\cell \row

\itap1\trowd \taflags0 \trgaph108\trleft-108 \trbrdrl\brdrnil \trbrdrt\brdrnil \trbrdrr\brdrnil 
\clvertalc \clshdrawnil \clwWidth2386\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx1234
\clvertalc \clshdrawnil \clwWidth773\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx2468
\clvertalc \clshdrawnil \clwWidth733\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx3702
\clvertalc \clshdrawnil \clwWidth1493\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx4937
\clvertalc \clshdrawnil \clwWidth1093\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx6171
\clvertalc \clshdrawnil \clwWidth1880\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx7405
\clvertalc \clshdrawnil \clwWidth1506\clftsWidth3 \clmart10 \clmarl10 \clmarb10 \clmarr10 \clbrdrt\brdrnil \clbrdrl\brdrnil \clbrdrb\brdrnil \clbrdrr\brdrnil \clpadt20 \clpadl20 \clpadb20 \clpadr20 \gaph\cellx8640
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 P6 Evolvability\cell 
\pard\intbl\itap1\pardeftab720\partightenfactor0
\cf0 Yes\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 2\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 1\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 3\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 2\cell 
\pard\intbl\itap1\pardeftab720\qr\partightenfactor0
\cf0 6\cell \lastrow\row
\pard\pardeftab720\sa240\partightenfactor0
\cf0 *P4 documented exception: this is a verification task (checking an artefact against stated requirements), where the two paradigms measured at parity rather than the default 1.5\'963\'d7 gap. Agent P4 capability is read as 3, not 2, for this row \'97 noted for completeness, though it doesn't affect the route.\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 M eligibility check:
\f1\b0  P2 is M with agent capability 1 
\f3 \uc0\u8594 
\f1  
\f2\b agent excluded from this comparative run.
\f1\b0  P3 is M with agent capability 2 
\f3 \uc0\u8594 
\f1  would remain eligible on its own, but doesn't matter once P2 excludes it. Workflow meets both M requirements at capability 3.\

\f2\b Result:
\f1\b0  Workflow is the only eligible paradigm \'97 
\f2\b route: workflow.
\f1\b0  (Recomputed workflow total: 6+9+9+9+6+6+2 = 47; agent total not reported, per rule.) Decisive row: P2 safe failure, same pattern as Triage \'97 mandatory and unattainable by the agent's measured failure direction.\

\f2\b Component rule applied to workflow:
\f1\b0 \
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls2\ilvl0\cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 P1, P2, P3, P4 at capability 3 
\f3 \uc0\u8594 
\f1  no additional component; capability threshold met, deployment validation still required.\
\ls2\ilvl0
\f2\b \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 T2 at capability 2, weight 3 
\f5 \uc0\u8594 
\f2  control mandatory:
\f1\b0  per-item calls plus a deterministic item-count guard \'97 i.e., each claim gets its own bound evidence-matching call, with a count check ensuring no claim is dropped from the mapping.\
\ls2\ilvl0
\f2\b \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 P5 at capability 2, weight 3 
\f5 \uc0\u8594 
\f2  control mandatory:
\f1\b0  an input-normalisation stage for messy/inconsistent draft or evidence formatting.\
\ls2\ilvl0
\f2\b \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 P6 at capability 1, weight 2 
\f5 \uc0\u8594 
\f2  residual risk:
\f1\b0  structural change to the verification rubric or policy rules requires explicit review and graph modification \'97 accepted limitation, revisit if the rubric changes often.\
\pard\pardeftab720\sa280\partightenfactor0

\f2\b\fs28 \cf0 3. Design knowledge\
\pard\pardeftab720\sa240\partightenfactor0

\fs24 \cf0 Mandatory minimum for this workflow verdict:
\f1\b0  one bounded re-plan round for empty/chained reads; a placeholder guard before dispatch; per-item calls with a deterministic count check; fail-closed conditions (no status while a check is unverified); a dev-slice pilot before freezing.\

\f2\b 01 \'97 Implementation and execution environment.
\f1\b0  This step touches no external systems \'97 it evaluates the draft against the already-supplied evidence package \'97 so the environment question is mainly about where verification logs and the claim-to-evidence trace are stored, given this feeds accountability for what gets sent under your name. If the five-criterion rubric or policy rules (P6 residual risk) may need editing by non-developers, keep them as an inspectable, separately-versioned ruleset rather than embedded in a single prompt.\

\f2\b 02 \'97 Build form.
\f1\b0  For the workflow paradigm: canonical two-stage, state machine, rule engine, per-item map, verification form. Based on your confirmed facts \'97 this is explicitly a checking task with a fixed five-criterion rubric \'97 the 
\f2\b verification form
\f1\b0  is the leading candidate: evaluate each of the five criteria separately, then aggregate the final status deterministically. Layer the 
\f2\b per-item map
\f1\b0  form on top specifically for the claim-to-evidence mapping (T2's control), since that's a per-item binding problem nested inside the broader verification. Note: the measured verification workflows failed toward the safer false-rejection side (more 
\f6\fs26 revision_required
\f1\fs24 /
\f6\fs26 manual_review
\f1\fs24  than warranted) rather than false-pass \'97 that's a known, acceptable-direction bias worth confirming holds for your rubric during the pilot.\

\f2\b 03 \'97 Build rules for this task.
\f1\b0 \
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls3\ilvl0
\f7\i \cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Data handling:
\f1\i0  Process each of the five criteria as its own bound sub-check, and each claim in the evidence mapping as its own bound item \'97 don't let one model call try to hold requests, claims, figures, placeholders, and tone all at once. Verify item counts (every claim from the draft appears in the mapping) deterministically.\
\ls3\ilvl0
\f7\i \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Execution structure:
\f1\i0  Five criteria plus N claims is a small, bounded fan-out \'97 no chunking needed, but cap the claim count explicitly as a safety measure.\
\ls3\ilvl0
\f7\i \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Security guards:
\f1\i0  Fail closed \'97 any criterion that can't be conclusively checked (ambiguous evidence, unclear claim) should push the status toward 
\f6\fs26 manual_review
\f1\fs24 , not 
\f6\fs26 pass
\f1\fs24 . This directly implements your mandatory P2.\
\ls3\ilvl0
\f7\i \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 State and monitoring:
\f1\i0  Validate the final aggregated status against the individual criterion results (e.g., code-check that 
\f6\fs26 pass
\f1\fs24  is only possible when all five sub-checks passed) rather than trusting the model's own aggregation \'97 this is where the deterministic layer catches errors a model judge alone would miss (measured: 11% of scored artefacts).\
\ls3\ilvl0
\f7\i \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Pilot before freeze:
\f1\i0  Run on a dev slice (~10 drafts, including some with deliberately planted unsupported claims and placeholder gaps) to confirm the rubric catches what it should before freezing.\
\ls3\ilvl0
\f7\i \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Compute, don't ask:
\f1\i0  Exact date/amount/name matching should be a deterministic string/value comparison against the evidence, never left to the model's judgment \'97 reserve the model for the harder judgment calls (tone, paraphrase-to-evidence matching).\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 04 \'97 Model check.
\f1\b0  This build requires the model to reliably match paraphrased or reworded claims back to their source evidence, and to judge tone/policy compliance \'97 your P5 (messy input) is critical here too, since drafts and evidence may be informally worded. Validate the concrete model specifically on cases with subtly unsupported claims (plausible-sounding but not actually in the evidence) and on borderline tone violations, since model judges have been shown to rate numerically or factually incorrect outputs as convincing \'97 pair every model judgment with the deterministic checks above rather than trusting it alone.\
\pard\pardeftab720\partightenfactor0
\cf3 \strokec3 \
\pard\pardeftab720\sa240\partightenfactor0
\cf0 \strokec2 All four routed tasks (Triage, Context Gathering, Draft Composition, Draft Verification) are now scored. Here's the complete decision record.\
\pard\pardeftab720\sa280\partightenfactor0

\f2\b\fs28 \cf0 Decision record\
\pard\pardeftab720\sa240\partightenfactor0

\fs24 \cf0 1. Triage
\f1\b0 \
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls4\ilvl0\cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Task and boundary: Classify a new email as 
\f6\fs26 requires_action
\f1\fs24  / 
\f6\fs26 no
\f1\fs24  / 
\f6\fs26 manual_review
\f1\fs24 , with category, priority, rationale, confidence.\
\ls4\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Gate outcome: None fired.\
\ls4\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Task fit: T1 applies (scored); T2, T3 not assessed as applicable.\
\ls4\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Performance profile: P1=3, P2=M, P3=M, P4=2, P5=3, P6=2. No hard cost/latency ceiling specified.\
\ls4\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Verdict: 
\f2\b Workflow
\f1\b0  (rule engine). Agent excluded by M (P2).\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 2. Context Gathering
\f1\b0 \
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls5\ilvl0\cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Task and boundary: Assemble a verified, sourced context package sufficient to answer the email, without drafting.\
\ls5\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Gate outcome: G4 fired (adaptive control flow); G5 would independently fire.\
\ls5\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Task fit: T1, T2, T3 confirmed not applicable \'97 no controls attached.\
\ls5\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Performance profile: P1=3, P2=M (deployment conflict \'97 resolved via deterministic post-check, not agent self-assessment), P3=3, P4=2, P5=3, P6=3. No hard cost/latency ceiling specified.\
\ls5\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Verdict: 
\f2\b Agent
\f1\b0  (ReAct loop), fixed by gate.\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 3a. Draft Composition
\f1\b0  
\f7\i (split from original "Draft generation," operation 1 of 2 on this lineage)
\f1\i0 \
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls6\ilvl0\cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Task and boundary: Produce subject + body addressing identified requests, in appropriate tone, from supplied verified context only.\
\ls6\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Gate outcome: None fired.\
\ls6\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Task fit: T1, T2, T3 not applicable.\
\ls6\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Performance profile: P1=3, P2=3, P3=3, P4=2, P5=3, P6=2. No hard cost/latency ceiling specified.\
\ls6\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Verdict: 
\f2\b Workflow
\f1\b0  (canonical two-stage). Workflow 41 vs. agent 34 \'97 genuine margin.\
\pard\pardeftab720\sa240\partightenfactor0

\f2\b \cf0 3b. Draft Verification
\f1\b0  
\f7\i (split from original "Draft generation")
\f1\i0 \
\pard\tx220\tx720\pardeftab720\li720\fi-720\partightenfactor0
\ls7\ilvl0\cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Task and boundary: Evaluate the draft against a five-criterion rubric (request coverage, evidence grounding, factual fidelity, completion integrity, tone/policy compliance) and produce status + claim-to-evidence mapping, without rewriting.\
\ls7\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Gate outcome: None fired (G3 explicitly does not fire \'97 checking, not producing).\
\ls7\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Task fit: T2 applies (scored); T1, T3 not applicable.\
\ls7\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Performance profile: P1=3, P2=M, P3=M, P4=2, P5=3, P6=2. No hard cost/latency ceiling specified.\
\ls7\ilvl0\kerning1\expnd0\expndtw0 \outl0\strokewidth0 {\listtext	\uc0\u8226 	}\expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 Verdict: 
\f2\b Workflow
\f1\b0  (verification form + per-item map for claim mapping). Agent excluded by M (P2).\
\pard\pardeftab720\sa280\partightenfactor0

\f2\b\fs28 \cf0 Architecture map\
\pard\pardeftab720\partightenfactor0

\f1\b0\fs24 \cf0 \
\pard\pardeftab720\sa260\partightenfactor0

\fs26 \cf0 V\
\pard\pardeftab720\partightenfactor0

\fs24 \cf0 visualize\
\pard\pardeftab720\sa207\partightenfactor0

\fs20\fsmilli10400 \cf0 V\
\pard\pardeftab720\partightenfactor0

\fs24 \cf0 visualize show_widget\
\
\
\
\pard\pardeftab720\sa240\partightenfactor0
\cf0 The connections shown (Triage 
\f3 \uc0\u8594 
\f1  Context gathering 
\f3 \uc0\u8594 
\f1  Draft generation 
\f3 \uc0\u8594 
\f1  human review) reflect only the order you described \'97 that's orchestration context, not a TADF output. Sequencing, triggers, and hand-offs between these tasks remain your decision as architect.\
Each task is now routed, with its design knowledge and constraints attached.\
\pard\pardeftab720\sa240\partightenfactor0
\cf0 This is where TADF ends. It provides task-level architecture decisions and the associated design knowledge. It does not determine system-level sequencing, triggers, hand-offs, or interfaces.\
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0 \cf0 \kerning1\expnd0\expndtw0 \outl0\strokewidth0 \
\
\
\
}