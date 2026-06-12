#!/usr/bin/env bash
set -euo pipefail

gate_profile="${GATE_PROFILE:-bootstrap-final-minimal}"
run_id="${RUN_ID:-not_provided}"
candidate_id="${CANDIDATE_ID:-not_provided}"
candidate_output="${CANDIDATE_OUTPUT:-}"
output_schema="${OUTPUT_SCHEMA:-}"
forbidden_regex="${FORBIDDEN_PATH_REGEX:-^\\.agent-runs/|^\\.git/}"

status="pass"
notes=()

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  status="fail"
  notes+=("not_a_git_work_tree")
  head_sha="missing"
  changed_files=""
  git_status=""
else
  head_sha="$(git rev-parse HEAD)"
  git_status="$(git status --short)"
  changed_files="$(git status --short | sed -E 's/^...//' | sort)"
fi

forbidden_path_check="pass"
if [ -n "${changed_files}" ] && printf '%s\n' "${changed_files}" | grep -E "${forbidden_regex}" >/dev/null 2>&1; then
  forbidden_path_check="fail"
  status="fail"
  notes+=("forbidden_path_changed")
fi

candidate_output_schema_check="not_configured"
if [ -n "${candidate_output}" ]; then
  if [ -f "${candidate_output}" ]; then
    if python3 -m json.tool "${candidate_output}" >/dev/null 2>&1; then
      if [ -z "${output_schema}" ]; then
        candidate_output_schema_check="fail"
        status="fail"
        notes+=("candidate_output_schema_missing")
      elif [ ! -f "${output_schema}" ]; then
        candidate_output_schema_check="fail"
        status="fail"
        notes+=("candidate_output_schema_file_missing")
      elif python3 scripts/validate-bootstrap-pack.py --schema "${output_schema}" --instance "${candidate_output}" >/dev/null 2>&1; then
        candidate_output_schema_check="pass"
      else
        candidate_output_schema_check="fail"
        status="fail"
        notes+=("candidate_output_schema_invalid")
      fi
    else
      candidate_output_schema_check="fail"
      status="fail"
      notes+=("candidate_output_not_json")
    fi
  else
    candidate_output_schema_check="fail"
    status="fail"
    notes+=("candidate_output_missing")
  fi
fi

cat <<EOF
gate_report:
  status: ${status}
  gate_profile: ${gate_profile}
  run_id: ${run_id}
  candidate_id: ${candidate_id}
  current_target_sha: ${head_sha}
  changed_files:
EOF

if [ -n "${changed_files}" ]; then
  printf '%s\n' "${changed_files}" | sed 's/^/    - /'
else
  echo "    []"
fi

cat <<EOF
  checks:
    git_status:
      status: pass
      output: |-
EOF

if [ -n "${git_status}" ]; then
  printf '%s\n' "${git_status}" | sed 's/^/        /'
else
  echo "        clean"
fi

cat <<EOF
    head_sha: pass
    changed_files: pass
    forbidden_path_check: ${forbidden_path_check}
    candidate_output_schema_check: ${candidate_output_schema_check}
    candidate_output_schema: ${output_schema:-not_configured}
    secret_scan: optional_not_configured
    lint: optional_not_configured
    typecheck: optional_not_configured
    tests: optional_not_configured
    build: optional_not_configured
  notes:
EOF

if [ "${#notes[@]}" -gt 0 ]; then
  for note in "${notes[@]}"; do
    echo "    - ${note}"
  done
else
  echo "    []"
fi

if [ "${status}" = "fail" ]; then
  exit 1
fi
