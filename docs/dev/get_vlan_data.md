# get_vlan_data — behavior and examples

References:
- [`get_vlan_data()`](nautobot_device_onboarding/jinja_filters.py:109)
- [`perform_data_extraction()`](nautobot_device_onboarding/nornir_plays/formatter.py:124)
- [`TestJinjaFilters`](nautobot_device_onboarding/tests/test_jinja_filters.py:22)
- [`TestFormatterExtractAndProcess`](nautobot_device_onboarding/tests/test_formatter.py:88)

Summary:
The `get_vlan_data` Jinja2 filter extracts VLAN information for a single interface item using a VLAN mapping.
It is used as a post_processor in command mappers and expects parsed command output structures.

Parameters
- item: the interface data to process. Common forms:
  - [] (empty list) — no data
  - [ {access_vlan, native_vlan, trunking_vlans, admin_mode, mode} ] — list with one dict
  - dict or list-of-one-dict (function normalizes single-element lists)
- vlan_mapping: dict mapping VLAN id string -> VLAN name, e.g. {"1": "default", "10": "DATA"}
  - If not a dict (e.g. list), function logs and returns []
- tag_type: "tagged" or "untagged" — which VLAN set to return

Return value
- A list of VLAN entries, each entry is {"id": <str>, "name": <str>}
- Empty list when no applicable VLANs

Core logic (high level)
1. Normalize item: if item is list of length 1, use item[0]
2. Determine interface mode by calling `interface_mode_logic(item)` (see tests)
   - returns values like "access", "tagged", "tagged-all", or ""
3. Handle "tagged-all":
   - if tag_type == "tagged": return []
   - if tag_type == "untagged": return native VLAN mapped as a single entry
4. For other modes:
   - tag_type == "untagged":
     - if mode == "access": return access_vlan if present
     - else return native_vlan (or default "1") mapped
   - tag_type == "tagged":
     - if mode == "access": return []
     - else expand trunking_vlans into list of VLAN IDs and map each to name

VLAN name resolution
- If vlan_mapping contains the VLAN id as string, use that name
- Otherwise generate default name "VLANxxxx" zero-padded to 4 digits (e.g. VLAN0012)

Interaction with helpers
- `interface_mode_logic` determines mode; tests assert expected outcomes
- `vlanconfig_to_list` is used to expand ranges like "1-4094" and string lists

Examples from tests
Example A — empty item
- Input:
  - item = []
  - vlan_mapping = []
  - tag_type = "tagged"
- Behavior: function detects vlan_mapping is list -> logs and returns []
- Test: `test_get_vlan_data_empty_item_data` expects []

Example B — tagged-all trunk, requesting tagged
- Input:
  - item = [{"access_vlan":"10","trunking_vlans":["ALL"]}]
  - vlan_mapping = {"10": "VLAN0010"}
  - tag_type = "tagged"
- Output: [] (tagged-all short-circuits)
- Test: `test_get_vlan_data_tagged_all_tagged_all`

Example C — tagged-all trunk, requesting tagged with range string
- Input:
  - item = [{"access_vlan":"10","trunking_vlans":["1-4094"]}]
  - vlan_mapping = {"10": "VLAN0010"}
  - tag_type = "tagged"
- Output: [] (still treated as tagged-all)
- Test: `test_get_vlan_data_tagged_all_tagged_range`

Example D — access port, untagged (access VLAN present)
- Input:
  - item = [{"access_vlan":"10","trunking_vlans":["1-4094"]}]
  - vlan_mapping = {"10": "DATA"}
  - tag_type = "untagged"
- Output: [{"id":"10","name":"DATA"}]
- Test: `test_get_vlan_data_access_create_defined_name`

Example E — trunk with single allowed VLAN, tagged
- Input:
  - item = [{"access_vlan":"10","trunking_vlans":["10"]}]
  - vlan_mapping = {"10": "DATA"}
  - tag_type = "tagged"
- Output: [{"id":"10","name":"DATA"}]
- Test: `test_get_vlan_data_access_tagged_vlans_defined_trunking_as_list`

Example F — trunk VLAN not in mapping -> default name
- Input:
  - item = [{"access_vlan":"10","trunking_vlans":["12"]}]
  - vlan_mapping = {"10": "DATA"}  # 12 missing
  - tag_type = "tagged"
- Output: [{"id":"12","name":"VLAN0012"}]
- Test: `test_get_vlan_data_access_tagged_vlans_no_name_trunking_as_list`

Implementation notes
- The function accepts both list-wrapped dicts and raw dicts via normalization
- Uses `chain.from_iterable` + `vlanconfig_to_list` to flatten trunk ranges and multiple stanzas
- Returns VLAN id as string for 'id' and name as resolved string

How it's used in command mappers
- `perform_data_extraction` calls `extract_and_post_process` which renders post_processor templates
- Example mapping in YAML uses `post_processor: "{{ obj | get_vlan_data(vlan_map, 'tagged') | tojson }}"`
- Pre-processor `vlan_map` is often generated earlier and passed into the Jinja context

Practical usage example (concrete)
- Suppose `vlan_map = {"1":"default","10":"DATA","20":"VOICE"}`
- For access port `item = [{"access_vlan":"20","trunking_vlans":"1-4094","native_vlan":"20","admin_mode":"access","mode":"access"}]`
- get_vlan_data(item, vlan_map, "untagged") -> [{"id":"20","name":"VOICE"}]

Edge cases
- Non-dict vlan_mapping (list) -> function logs and returns []
- Missing fields (no native_vlan or access_vlan) -> default native 1 used for untagged
- trunking_vlans as string -> converted to list before expansion

See also
- [`perform_data_extraction()`](nautobot_device_onboarding/nornir_plays/formatter.py:124)
- Command mappers in [`nautobot_device_onboarding/command_mappers/`](nautobot_device_onboarding/command_mappers/)

-- end of document