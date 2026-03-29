#' Aggregate Search Trends Data by Time Interval
#'
#' This function aggregates search trends data by month, week, or day based on a user-specified parameter. The function
#' uses lubridate's month(), week(), and day() functions to aggregate the data, and includes a max(time) grouping variable
#' for the given time interval.
#'
#' @param df A data frame of search trends data.
#' @param interval A character string indicating the time interval to use for aggregation: "month", "week", or "day".
#' @param id_col A character string indicating the column name for the ID variable to group by.
#' @param value_col A character string indicating the column name for the value variable to aggregate.
#'
#' @return A tibble with aggregated search trends data grouped by ID variable and time interval.
#'
#' @examples
#' trend_aggregate(search_trends, "month", "id", "value")
#'
#' @importFrom dplyr group_by summarise arrange mutate ungroup
#' @importFrom lubridate month week day
#' @export
trend_aggregate <- function(df, interval, id_col, value_col) {
  # Check for valid interval parameter
  if (!(interval %in% c("month", "week", "day"))) {
    stop("Interval parameter must be one of 'month', 'week', or 'day'")
  }
  
  interval_fn<-switch(interval, "month" = lubridate::month, "week" = lubridate::week, "day" = lubridate::day)
  # Aggregate data by specified interval
  df %>%
    group_by(.data[[id_col]], interval_fn(time)) %>%
    summarise(value = sum(.data[[value_col]], na.rm = TRUE),
              max_time = max(time),
              .groups = "drop") %>%
    group_by(.data[[id_col]]) %>%
    mutate(tot_val = sum(value, na.rm = TRUE))%>%
    ungroup() %>%
    mutate(rank = dense_rank(desc(tot_val))) %>%
    rename(!!sym(interval) := `interval_fn(time)`,
           search_terms = id)
}
