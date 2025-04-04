

function prs

  function addLineStart
    set -l line0 (string join " " $argv)
    set -g printed_lines (string join "" $line0 $printed_lines)
  end

  function addLine
    set -l line1 (string join " " $argv)
    set -g printed_lines (string join "\n" $printed_lines $line1)
  end

  function addSameLine
    set -l line2 (string join " " $argv)
    set -g printed_lines (string join " " $printed_lines $line2)
  end

  function load_env_vars
      set -l envfile "$HOME/.prs.env"
      if test -f $envfile
          for line in (cat $envfile)
              if test -n "$line"
                  set key (echo $line | cut -d'=' -f1)
                  set val (echo $line | cut -d'=' -f2-)
                  set val (string trim --chars='"' -- $val)

                  if test -n "$val"
                      switch $key
                          case "REPO"
                              set -g repo $val
                          case "USERNAME"
                              set -g username $val
                          case "CHECK_ONLY"
                              if contains $val 0 1
                                  set -g checks_only $val
                              end
                          case "CHECK_DETAILED"
                              if contains $val 0 1
                                  set -g checks_detailed $val
                              end
                          case "REVIEWS_ONLY"
                              if contains $val 0 1
                                  set -g reviews_only $val
                              end
                          case "REVIEWS_DETAILED"
                              if contains $val 0 1
                                  set -g reviews_detailed $val
                              end
                          case "LABELS_ONLY"
                              if contains $val 0 1
                                  set -g labels_only $val
                              end
                          case "LABELS_DETAILED"
                              if contains $val 0 1
                                  set -g labels_detailed $val
                              end
                          case "SHOW_URL"
                              if contains $val 0 1
                                  set -g show_url $val
                              end
                          case "SHOW_BRANCH"
                              if contains $val 0 1
                                  set -g show_branch $val
                              end
                          case "SHOW_DRAFTS"
                              if contains $val 0 1
                                  set -g show_pr_in_draft $val
                              end
                      end
                  end
              end
          end
      end


    set only_vars $checks_only $reviews_only $labels_only

    for isOn in $only_vars
        if contains isOn 1
          set -g show_only_selected 1
        end
    end
  end

  function help_info
    echo "Usage: prs [OPTIONS]"
    echo ""
    echo "To Change the user preferences, edit the file:"
    echo -e "\t" "$HOME/.prs.env"
    echo ""
    echo "Options:"
    echo "  -d, --draft        Include draft PRs."
    echo "  -h, --help         Display this help message."
    echo "  -c, --checks       Show/Hide CHECKS detailed information."
    echo "  -C                 Only display CHECKS."
    echo "  -r, --reviews      Show/Hide REVIEWS detailed information."
    echo "  -R                 Only display REVIEWS."
    echo "  -l, --labels       Show/Hide LABELS detailed information."
    echo "  -L                 Only display LABELS."
    echo "  --save             Saves the current flags in the .prs.env file."
  end

  function update_env_var
      set -l key $argv[1]
      set -l value $argv[2]
      set -l envfile "$HOME/.prs.env"
      set -l tempfile (mktemp)

      if test -z "$key" -o -z "$value"
          echo "Usage: update_env_var KEY VALUE"
          return 1
      end

      if not test -f $envfile
          echo "❌ Env file not found at $envfile"
          return 1
      end

      set -l updated 0
      # Read file line by line and write to tempfile
      while read -l line
          set name (string split -m1 "=" $line)[1]
          if test "$name" = "$key"
              echo "$key=$value" >> $tempfile
              set updated 1
          else
              echo $line >> $tempfile
          end
      end < $envfile

      # If the key was not present, append it
      if test $updated -eq 0
          echo "$key=$value" >> $tempfile
      end

      mv $tempfile $envfile
  end

  function check_vars_to_update
    set should_update 0
    for arg in $argv
      if test $arg = "--save"
          set should_update 1
      end
    end

    if test $should_update -eq 1
        # # update_env_var REPO $repo
        # # update_env_var USERNAME $username
        update_env_var 'CHECK_ONLY' $checks_only
        update_env_var 'CHECK_DETAILED' $checks_detailed
        update_env_var 'REVIEWS_ONLY' $reviews_only
        update_env_var 'REVIEWS_DETAILED' $reviews_detailed
        update_env_var 'LABELS_ONLY' $labels_only
        update_env_var 'LABELS_DETAILED' $labels_detailed
        update_env_var 'SHOW_URL' $show_url
        update_env_var 'SHOW_BRANCH' $show_branch
        update_env_var 'SHOW_DRAFTS' $show_pr_in_draft
        echo -e "✅ Updated configs"
        return 0
    end

    return 1
  end

  function check_optional_commands
    for arg in $argv
      switch $arg
        case -h --help
          help_info
          return 0
        case -d --draft
          set -g show_pr_in_draft (math "1 - $show_pr_in_draft")
        case -c --checks
          set -g checks_detailed (math "1 - $checks_detailed")
        case -r --reviewers
          set -g reviews_detailed (math "1 - $reviews_detailed")
        case -l --labels
          set -g labels_detailed (math "1 - $labels_detailed")
        case -C
          set -g checks_only (math "1 - $checks_only")
          set -g show_only_selected (math "1 - $show_only_selected")
        case -R 
          set -g reviews_only (math "1 - $reviews_only")
          set -g show_only_selected (math "1 - $show_only_selected")
        case -L
          set -g labels_only (math "1 - $labels_only")
          set -g show_only_selected (math "1 - $show_only_selected")
      end
    end
    return 1
  end

  function global_vars
      # Default values
      #? Usage: Git vars
      set -g repo anchorlabsinc/anchorage
      set -g username @me
      #? Configs
      set -g show_url 0
      set -g show_branch 0
      set -g show_pr_in_draft 0
      #? Sections
      set -g checks_only 0
      set -g checks_detailed 0
      set -g reviews_only 0
      set -g reviews_detailed 0
      set -g labels_only 0
      set -g labels_detailed 0
      #? 
      set -g show_only_selected 0
      set -g draft_number 0

      set -g dangList "skip-ci" "conflict" "do-not-merge" "no-reviewers"
      set -g warnList "force-ci" "ignore-fe-cache" "skip-second-review"
      set -g goodList "ready-after-ci" "ready-to-merge" "deploy-pr-backoffice" "deploy-pr-frontoffice"
  end

  function print_checks
      set pr $argv[1]
      set total 0
      set pendingCount 0
      set failingCount 0
      set successCount 0
      for check in (echo $pr | jq -c '.statusCheckRollup[]?')
          set state (echo $check | jq -r '.state')
          set context (echo $check | jq -r '.context')
          if test "$state" != "null" -a "$context" != "null"
              set total (math $total + 1)
              if test "$state" = "SUCCESS"
                  set successCount (math $successCount + 1)
              else if test "$state" = "PENDING"
                  set pendingCount (math $pendingCount + 1)
              else if test "$state" = "FAILURE" -o "$state" = "FAILED"
                  set failingCount (math $failingCount + 1)
              end
          end
      end

      addLine "\tChecks:"
      if test $total -eq $successCount
          addSameLine (set_color green)
          addSameLine "ALL TESTS PASSED"
      else if test $failingCount -gt 0
          addSameLine (set_color red)
          addSameLine "FAILURE #"$failingCount
      else if test $pendingCount -gt 0
          addSameLine (set_color yellow)
          addSameLine "PENDING #"$$pendingCount
      else
          addSameLine (set_color green)
          addSameLine "ALL TESTS PASSED"
      end
          addSameLine (set_color normal)
  end

  function print_checks_detailed
      addLine "\tChecks:"

      set pr $argv[1]
      set -l stateCounter 0
      set -l hasPassedChecks 0
      for check in (echo $pr | jq -c '.statusCheckRollup[]?')
          set state (echo $check | jq -r '.state')
          set context (echo $check | jq -r '.context')
          if test "$state" != "null" -a "$context" != "null"
              set stateCounter (math $stateCounter + 1)
              set color green
              if test "$state" = "FAILURE" -o "$state" = "FAILED"
                  set color red
              else if test "$state" = "PENDING"
                  set color yellow
              end

              if test "$color" = "green"
                  set hasPassedChecks (math $hasPassedChecks + 1)
              end
              set formatted_state (set_color $color)(printf "%-12s" $state)(set_color normal)

              addLine "\t\t"$formatted_state $context
          end
      end
  end

  function print_reviews
      addLine "\tReview:"
      set pr $argv[1]
      # Retrieve the review decision from the PR JSON
      set review_decision (echo $pr | jq -r '.reviewDecision')

      set color green
      if test "$review_decision" = "APPROVED"
          set color green
      else if test "$review_decision" = "REVIEW_REQUIRED"
          set color yellow
      else
          set color red
      end
      addSameLine (set_color $color)$review_decision(set_color normal)
  end

  function print_reviews_detailed
      addLine "\tReview:"
      set pr $argv[1]

      # List individual reviewers with their review state
      echo $pr | jq -c '.reviews | sort_by(.submittedAt) | reverse | unique_by(.author.login)[]?' | while read review
          set user (echo $review | jq -r '.author.login')
          set state (echo $review | jq -r '.state')
          set color green
          if test "$state" = "CHANGES_REQUESTED"
              set color red
          else if test "$state" = "COMMENTED"
              set color yellow
          end

          set formatted_state (set_color $color)(printf "%-14s" $state)(set_color normal)

          addLine "\t\t"$formatted_state $user
      end
  end

  function print_labels
      set pr $argv[1]
      set labels (echo $pr | jq -r '.labels[].name?')
      set summary_labels

      addLine "\tLabels:"
      for label in $labels
          if contains $label $dangList
              set summary_labels $summary_labels (set_color red)$label(set_color normal)
          else if contains $label $warnList
              set summary_labels $summary_labels (set_color yellow)$label(set_color normal)
          else if contains $label $goodList
              set summary_labels $summary_labels (set_color green)$label(set_color normal)
          end
      end

      if test (count $summary_labels) -gt 0
          set joined (string join ", " $summary_labels)
          addSameLine $joined
      else
          addSameLine (set_color brblack)
          addSameLine "No relevant labels to show"
          addSameLine (set_color normal)
      end
  end

  function print_labels_detailed
      set pr $argv[1]
      set labels (echo $pr | jq -r '.labels[].name?')

      addLine "\tLabels:"
      if test -z "$labels"
        addSameLine (set_color brblack)
        addSameLine "No labels"
      else
          for label in $labels
              if contains $label $dangList
                  addLine "\t\t"
                  addSameLine (set_color red)
                  addSameLine $label
              else if contains $label $warnList
                  addLine "\t\t"
                  addSameLine (set_color yellow)
                  addSameLine $label
              else if contains $label $goodList
                  addLine "\t\t"
                  addSameLine (set_color green)
                  addSameLine $label
              else
                  addLine "\t\t"
                  addSameLine (set_color brblack)
                  addSameLine $label
              end
          end
      end
      addSameLine (set_color normal)
  end
    
  # load global variables
  global_vars
  
  # Load config overrides
  load_env_vars

  # check for optional commands
  if check_optional_commands $argv 
    return 0
  end

  if check_vars_to_update $argv
    return 0
  end

  set prs (gh pr list --repo $repo --author $username -L 50 --state open --json number,title,headRefName,url,isDraft,statusCheckRollup,reviewDecision,labels,reviews | jq -c '.[]')

  for pr in $prs
    set -g printed_lines ""
    set number (echo $pr | jq -r '.number')
    set title (echo $pr | jq -r '.title')
    set branch (echo $pr | jq -r '.headRefName')
    set url (echo $pr | jq -r '.url')
    set review_decision (echo $pr | jq -r '.reviewDecision')
    set draft (echo $pr | jq -r '.isDraft')
    
    if test "$show_pr_in_draft" = "0" -a "$draft" = "true"
        set -g draft_number (math $draft_number + 1)
        continue
    end

    # if test $show_url -eq 1 and $show_only_selected -eq 0 
    if test $show_url -eq 1
      addLine "\tPR Url:"
      addSameLine (set_color brwhite)$url(set_color normal)
    end

    # if test $show_branch -eq 1 and $show_only_selected -eq 0 
    if test $show_branch -eq 1
      addLine "\tBranch:"
      addSameLine (set_color cyan)$branch(set_color normal)
    end


    if test $show_only_selected -eq 0 -o (math $show_only_selected + $checks_only) -eq 2
      if test $checks_detailed -eq 1
        print_checks_detailed $pr
      else
        print_checks $pr
      end
    end

    if test $show_only_selected -eq 0 -o (math $show_only_selected + $reviews_only) -eq 2
      if test $reviews_detailed -eq 1
        print_reviews_detailed $pr
      else
        print_reviews $pr
      end
    end

    if test $show_only_selected -eq 0 -o (math $show_only_selected + $labels_only) -eq 2
      if test $show_only_selected -eq 0 -o (math $show_only_selected + $labels_only) -eq 2
        if test $labels_detailed -eq 1
          print_labels_detailed $pr
        else
          print_labels $pr
        end
      end
    end

    set title_color blue

    if test "$draft" = "true"
        set title_color brblack
    end

    addLineStart (set_color brblack)"#"$number(set_color normal) (set_color $title_color)"$title"(set_color normal)

    echo -e $printed_lines
    echo
  end

  if test $draft_number -gt 0
      echo -e (set_color brblack)"There are "(set_color normal)"$draft_number"(set_color brblack)" PRs are drafts. `-d` to show them"(set_color normal)
  end
end