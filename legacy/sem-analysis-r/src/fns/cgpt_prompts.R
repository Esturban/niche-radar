#
#
#
#cgpt_prompts
keyword_gen_prompt <-
  function(terms = "Data Strategy Consulting Services", amount = 100) {
    paste0(
      "Generate a list of ",
      amount,
      " keywords closely related to ",
      terms,
      " without duplicating any words or common search terms. please list keywords in a comma separated list only."
    )
  }