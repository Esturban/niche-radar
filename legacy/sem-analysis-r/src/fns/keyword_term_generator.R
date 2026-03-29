keyword_term_generator <-
  function(file_loc = here::here("data", "eva-batch-usa", "keywords.RDS"),
           terms,
           amount,
           disclaimer = " Please ensure that the keywords generated are related to common ways someone might search up the corresponding services and find a service provider") {
    if (file.exists(file_loc))
      existing_keywords <- readRDS(file_loc)
    else
      existing_keywords <- NULL
    
    ek_prompt <-
      ifelse(
        is.null(existing_keywords),
        "",
        paste0(
          "Please do not repeat the following terms: ",
          paste0(existing_keywords, collapse = ",")
        )
      )
    ask_chatgpt(paste0(
      keyword_gen_prompt(terms = terms, amount = amount),
      disclaimer,
      ek_prompt
    )) -> generated_keywords
    
    all_terms<-paste0(
      paste0(generated_keywords,","),
      paste0(existing_keywords, collapse = ","),
      collapse = ","
    )%>%strsplit(x=.,",")%>%unlist(.)%>%trimws(.)%>%unique(.)
    saveRDS(all_terms,file_loc)
    return(all_terms)
  }
