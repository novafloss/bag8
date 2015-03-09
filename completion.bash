_bag8_completion() {
    COMPREPLY=( $( COMP_WORDS="${COMP_WORDS[*]}" \
                   COMP_CWORD=$COMP_CWORD \
                   _BAG8_COMPLETE=complete $1 ) )
    return 0
}

complete -F _bag8_completion -o default bag8;
