# Campaign ledger

ID: ee978718-7c9b-49ca-b98a-d5d2833e88f6
State: COMPLETED
Revision: 33

## Objective

Research-only EGFR analogue prioritization

## Events

- 2026-10-28T05:17:15.139133+00:00 created: {"objective": "EGFR wild-type analogue prioritization: research predictions only"}
- 2026-10-28T05:17:20.424292+00:00 transition: {"from": "DRAFT", "to": "PLANNING"}
- 2026-10-28T05:17:28.798163+00:00 transition: {"from": "PLANNING", "to": "AWAITING_PLAN_APPROVAL"}
- 2026-10-28T05:17:28.810206+00:00 approved: {"acting_role": "scientist", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "1847905e76c1f6e2f7268ebd19752b5eef73076225af321afb203f475d47ff1b", "id": "493cd384-53a5-4111-8df1-fc012b57ebc3", "kind": "plan"}
- 2026-10-28T05:17:28.810206+00:00 transition: {"from": "AWAITING_PLAN_APPROVAL", "to": "FORMULATING"}
- 2026-10-28T05:17:34.234529+00:00 transition: {"from": "FORMULATING", "to": "AWAITING_SCORE_APPROVAL"}
- 2026-10-28T05:17:34.321096+00:00 approved: {"acting_role": "scientist", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "052da3577207bf2706e13b54bbb66913168d9a2cd1120f1e53199c757b0746f1", "id": "5269c5a7-ea8f-42c7-9583-29b300adbd5b", "kind": "score"}
- 2026-10-28T05:17:34.321096+00:00 transition: {"from": "AWAITING_SCORE_APPROVAL", "to": "CONFIGURING"}
- 2026-10-28T05:17:48.082793+00:00 transition: {"from": "CONFIGURING", "to": "AWAITING_LAUNCH_APPROVAL"}
- 2026-10-28T05:17:48.311226+00:00 approved: {"acting_role": "operator", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "41a64d8ac6b4669105b2bb6c65e2bd5f282b29653cc2d709da5b1a6c055dae04", "id": "63330f47-c221-4f6f-b887-2c1f40c9a5e8", "kind": "launch"}
- 2026-10-28T05:17:48.311226+00:00 transition: {"from": "AWAITING_LAUNCH_APPROVAL", "to": "QUEUED"}
- 2026-10-28T05:17:48.435906+00:00 transition: {"from": "QUEUED", "to": "RUNNING"}
- 2026-10-28T05:17:48.435906+00:00 launch_reserved: {"approval": "63330f47-c221-4f6f-b887-2c1f40c9a5e8", "job_id": "3abc272f-4b7f-4336-963a-542825fa3b3a"}
- 2026-10-28T05:17:57.152314+00:00 engine_started: {"job_id": "3abc272f-4b7f-4336-963a-542825fa3b3a", "pid": 14248}
- 2026-10-28T05:18:33.285837+00:00 job_succeeded: {"artifacts": [{"path": "outputs\\iteration-0\\executed.json", "sha256": "9feeef1434cb9dc3bfc4cfe923a3c0ea972ea47170ce3ae092508b0808434583", "size": 1351}, {"path": "outputs\\iteration-0\\samples.csv", "sha256": "2749ace106a8f2aa98185405b838c785de5d4c7d65f83e43681b9c4c24269044", "size": 5368}, {"path": "jobs\\3abc272f-4b7f-4336-963a-542825fa3b3a\\engine.log", "sha256": "b007dd663967126ec27d8978a706f389fcfbc3ad202d375f66238b2b793cb8bf", "size": 4789}, {"path": "jobs\\3abc272f-4b7f-4336-963a-542825fa3b3a\\approved.toml", "sha256": "41a64d8ac6b4669105b2bb6c65e2bd5f282b29653cc2d709da5b1a6c055dae04", "size": 823}], "config_sha256": "41a64d8ac6b4669105b2bb6c65e2bd5f282b29653cc2d709da5b1a6c055dae04", "elapsed_seconds": 44.625, "exit_code": 0, "job_id": "3abc272f-4b7f-4336-963a-542825fa3b3a", "status": "succeeded"}
- 2026-10-28T05:18:33.286838+00:00 transition: {"from": "RUNNING", "to": "EVALUATING"}
- 2026-10-28T05:18:45.461333+00:00 transition: {"from": "EVALUATING", "to": "ANALYSING"}
- 2026-10-28T05:18:45.467969+00:00 transition: {"from": "ANALYSING", "to": "AWAITING_REVISION_APPROVAL"}
- 2026-10-28T05:18:45.476554+00:00 approved: {"acting_role": "scientist", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "a0d51764d7fe7ecfba44c61f513e7f53c9873a1a2fec88cee2ca6aadaf68e976", "id": "d4f3551a-3d52-4158-a18c-dd2d495f8ca7", "kind": "revision"}
- 2026-10-28T05:18:45.476554+00:00 transition: {"from": "AWAITING_REVISION_APPROVAL", "to": "PLANNING"}
- 2026-10-28T05:18:49.869213+00:00 transition: {"from": "PLANNING", "to": "AWAITING_PLAN_APPROVAL"}
- 2026-10-28T05:18:49.877132+00:00 approved: {"acting_role": "scientist", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "87ed4e5bdf9cc5c4796426ca187ed2278101170b8ec3c22ed880cee34f14d597", "id": "e2e7bd49-f9f1-4bab-8aee-36a867d77148", "kind": "plan"}
- 2026-10-28T05:18:49.878132+00:00 transition: {"from": "AWAITING_PLAN_APPROVAL", "to": "FORMULATING"}
- 2026-10-28T05:18:53.335681+00:00 transition: {"from": "FORMULATING", "to": "AWAITING_SCORE_APPROVAL"}
- 2026-10-28T05:18:53.420339+00:00 approved: {"acting_role": "scientist", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "052da3577207bf2706e13b54bbb66913168d9a2cd1120f1e53199c757b0746f1", "id": "ec328fe1-a05f-4629-a2e0-c4791b53900c", "kind": "score"}
- 2026-10-28T05:18:53.420339+00:00 transition: {"from": "AWAITING_SCORE_APPROVAL", "to": "CONFIGURING"}
- 2026-10-28T05:18:59.142941+00:00 transition: {"from": "CONFIGURING", "to": "AWAITING_LAUNCH_APPROVAL"}
- 2026-10-28T05:18:59.694632+00:00 approved: {"acting_role": "operator", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "7b4b607ec8c675a2a2989ac708335b8015e06c6246244973ca7704c97c109464", "id": "50c6d5bd-1c6d-4443-b34f-78ca6dbf79cc", "kind": "launch"}
- 2026-10-28T05:18:59.694632+00:00 transition: {"from": "AWAITING_LAUNCH_APPROVAL", "to": "QUEUED"}
- 2026-10-28T05:19:00.161426+00:00 transition: {"from": "QUEUED", "to": "RUNNING"}
- 2026-10-28T05:19:00.161426+00:00 launch_reserved: {"approval": "50c6d5bd-1c6d-4443-b34f-78ca6dbf79cc", "job_id": "83550deb-acdd-4ede-864c-7e39914fa53c"}
- 2026-10-28T05:19:10.138202+00:00 engine_started: {"job_id": "83550deb-acdd-4ede-864c-7e39914fa53c", "pid": 9452}
- 2026-10-28T05:19:45.563592+00:00 job_succeeded: {"artifacts": [{"path": "outputs\\iteration-0\\executed.json", "sha256": "9feeef1434cb9dc3bfc4cfe923a3c0ea972ea47170ce3ae092508b0808434583", "size": 1351}, {"path": "outputs\\iteration-0\\samples.csv", "sha256": "2749ace106a8f2aa98185405b838c785de5d4c7d65f83e43681b9c4c24269044", "size": 5368}, {"path": "outputs\\iteration-1\\executed.json", "sha256": "63c4777d8317483964cf98fec487aecf94257ca082f3874645258df622a5e71d", "size": 3050}, {"path": "outputs\\iteration-1\\optimized.chkpt", "sha256": "b218dc8716ef360feaffba4eef9c35430686eac390d4a22cff0e13efb4b4cc3f", "size": 80193995}, {"path": "outputs\\iteration-1\\rl_1.csv", "sha256": "088c3e4a4fc8ae103347063c889c05d0c10bc8ae77e0dbc6aa7b4931d3f2ca80", "size": 4611}, {"path": "jobs\\83550deb-acdd-4ede-864c-7e39914fa53c\\engine.log", "sha256": "419f013b2795b6cc01e0d24cc153f9a71e43032a4cfc11fce88ba0d6dbddceb5", "size": 15695}, {"path": "jobs\\83550deb-acdd-4ede-864c-7e39914fa53c\\approved.toml", "sha256": "7b4b607ec8c675a2a2989ac708335b8015e06c6246244973ca7704c97c109464", "size": 1839}], "config_sha256": "7b4b607ec8c675a2a2989ac708335b8015e06c6246244973ca7704c97c109464", "elapsed_seconds": 45.171999999991385, "exit_code": 0, "job_id": "83550deb-acdd-4ede-864c-7e39914fa53c", "status": "succeeded"}
- 2026-10-28T05:19:45.564600+00:00 transition: {"from": "RUNNING", "to": "EVALUATING"}
- 2026-10-28T05:19:57.281158+00:00 transition: {"from": "EVALUATING", "to": "ANALYSING"}
- 2026-10-28T05:19:57.287191+00:00 transition: {"from": "ANALYSING", "to": "AWAITING_REVISION_APPROVAL"}
- 2026-10-28T05:19:57.295365+00:00 approved: {"acting_role": "scientist", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "671df080fab2f408e22a2a6e7101f606b4113913074a527d80441b9767046b84", "id": "4790dc92-7dca-4931-9ea7-f8c57fa1c075", "kind": "revision"}
- 2026-10-28T05:19:57.295365+00:00 transition: {"from": "AWAITING_REVISION_APPROVAL", "to": "PLANNING"}
- 2026-10-28T05:20:01.681390+00:00 transition: {"from": "PLANNING", "to": "AWAITING_PLAN_APPROVAL"}
- 2026-10-28T05:20:01.689418+00:00 approved: {"acting_role": "scientist", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "8a5219dc374635b408ac7ffa8f6d438ab4eeada712294125ee70d4604f39dd32", "id": "5c9c9cc2-699d-4e8c-88bd-6d6372a02a24", "kind": "plan"}
- 2026-10-28T05:20:01.689418+00:00 transition: {"from": "AWAITING_PLAN_APPROVAL", "to": "FORMULATING"}
- 2026-10-28T05:20:05.239570+00:00 transition: {"from": "FORMULATING", "to": "AWAITING_SCORE_APPROVAL"}
- 2026-10-28T05:20:05.313126+00:00 approved: {"acting_role": "scientist", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "052da3577207bf2706e13b54bbb66913168d9a2cd1120f1e53199c757b0746f1", "id": "8d2fadde-05fc-4338-ac6a-72de702c1da3", "kind": "score"}
- 2026-10-28T05:20:05.313126+00:00 transition: {"from": "AWAITING_SCORE_APPROVAL", "to": "CONFIGURING"}
- 2026-10-28T05:20:10.894578+00:00 transition: {"from": "CONFIGURING", "to": "AWAITING_LAUNCH_APPROVAL"}
- 2026-10-28T05:20:11.197460+00:00 approved: {"acting_role": "operator", "actor": "harsh", "comments": "Owner requested implementation and bounded free local demonstration through Stage 7. Automated approval under that delegated development scope; not independent medicinal-chemist signoff.", "hash": "961b5c2560f70d2488f823b48fced879f17a701a6b11b0f03545d8b7daebeeb1", "id": "072f47e1-6995-43a1-a9c7-e15f92729254", "kind": "launch"}
- 2026-10-28T05:20:11.197460+00:00 transition: {"from": "AWAITING_LAUNCH_APPROVAL", "to": "QUEUED"}
- 2026-10-28T05:20:11.407677+00:00 transition: {"from": "QUEUED", "to": "RUNNING"}
- 2026-10-28T05:20:11.407677+00:00 launch_reserved: {"approval": "072f47e1-6995-43a1-a9c7-e15f92729254", "job_id": "15f6a5bb-419e-47d4-8217-ce4ebce83f11"}
- 2026-10-28T05:20:19.826564+00:00 engine_started: {"job_id": "15f6a5bb-419e-47d4-8217-ce4ebce83f11", "pid": 12848}
- 2026-10-28T05:20:49.022728+00:00 job_succeeded: {"artifacts": [{"path": "outputs\\iteration-0\\executed.json", "sha256": "9feeef1434cb9dc3bfc4cfe923a3c0ea972ea47170ce3ae092508b0808434583", "size": 1351}, {"path": "outputs\\iteration-0\\samples.csv", "sha256": "2749ace106a8f2aa98185405b838c785de5d4c7d65f83e43681b9c4c24269044", "size": 5368}, {"path": "outputs\\iteration-1\\executed.json", "sha256": "63c4777d8317483964cf98fec487aecf94257ca082f3874645258df622a5e71d", "size": 3050}, {"path": "outputs\\iteration-1\\optimized.chkpt", "sha256": "b218dc8716ef360feaffba4eef9c35430686eac390d4a22cff0e13efb4b4cc3f", "size": 80193995}, {"path": "outputs\\iteration-1\\rl_1.csv", "sha256": "088c3e4a4fc8ae103347063c889c05d0c10bc8ae77e0dbc6aa7b4931d3f2ca80", "size": 4611}, {"path": "outputs\\iteration-2\\executed.json", "sha256": "e560dfc89f6da9dcee53eb649a9895b2c7a5ec636fa49ae8cc1f1f02014a933e", "size": 1353}, {"path": "outputs\\iteration-2\\samples.csv", "sha256": "84554cc097f28350395a0407e0c5fe9e603a721af3aa1cb96b055f69ddd1d8c9", "size": 3592}, {"path": "jobs\\15f6a5bb-419e-47d4-8217-ce4ebce83f11\\engine.log", "sha256": "6b03c86d682591418e6185483dd8de81505fef5ad4996739edbf8e4ed83b3c55", "size": 4813}, {"path": "jobs\\15f6a5bb-419e-47d4-8217-ce4ebce83f11\\approved.toml", "sha256": "961b5c2560f70d2488f823b48fced879f17a701a6b11b0f03545d8b7daebeeb1", "size": 825}], "config_sha256": "961b5c2560f70d2488f823b48fced879f17a701a6b11b0f03545d8b7daebeeb1", "elapsed_seconds": 37.405999999988126, "exit_code": 0, "job_id": "15f6a5bb-419e-47d4-8217-ce4ebce83f11", "status": "succeeded"}
- 2026-10-28T05:20:49.022728+00:00 transition: {"from": "RUNNING", "to": "EVALUATING"}
- 2026-10-28T05:20:56.939447+00:00 transition: {"from": "EVALUATING", "to": "ANALYSING"}
- 2026-10-28T05:20:57.051468+00:00 transition: {"from": "ANALYSING", "to": "COMPLETED"}
