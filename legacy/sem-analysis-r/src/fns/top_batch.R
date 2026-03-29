#' Find Lowest Rank Search Terms and Create Batches for Re-Running Trend Values
#'
#' This function takes a tibble of search trends data and finds the N terms with the lowest rank value, and creates
#' batches of size M for re-running the relative trend value of those terms.
#'
#' @param df A tibble of search trends data with columns "id", "month", "value", "max_time", "tot_val", and "rank".
#' @param num_terms An integer indicating the number of terms with the lowest rank value to select.
#' @param batch_size An integer indicating the size of each batch for re-running the relative trend value of the selected terms.
#'
#' @return A tibble with the selected search terms and their batch assignment.
#'
#' @examples
#' top_batch(search_trends, 10, 2)
#'
#' @importFrom dplyr filter mutate
#' @export
top_batch <- function(df, num_terms, batch_size) {
  # Find the N terms with the lowest rank value
  top_items <- df %>%
    dplyr::filter(rank <= num_terms) %>%
    dplyr::mutate(batch = (rank) %% batch_size)
  
  return(top_items)
}