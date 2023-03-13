#' Search for Category Batches
#'
#' This function takes a vector of search terms and returns a tibble of unique
#' search categories, with a specified batch size. Optionally, you can provide a
#' vector of unused terms to exclude from the results.
#'
#' @param terms A vector of search terms.
#' @param size The desired batch size. Defaults to 5.
#' @param unused_terms An optional vector of search terms to exclude from the results.
#'
#' @return A tibble with a single column named "search_categories", containing unique
#' search categories grouped into batches of size "size".
#'
#' @examples
#' search_category_batches(c("apple", "orange", "banana", "peach"))
#'
#' @importFrom dplyr filter group_by row_number ungroup tibble
#' @export
search_category_batches<-function(terms,size = 5,unused_terms = NULL){
  tibble(search_terms = unique(c(terms))) %>%
    dplyr::filter(
      !search_terms %in% unused_terms
    ) %>%
    unique(.) %>%
    group_by(batch = row_number() %% round(nrow(.)/size,0)) %>%
    ungroup(.)
}
