#' Get Google Trends Data by Batch
#'
#' This function takes a data frame of search categories grouped into batches, and retrieves Google Trends data
#' for each batch. The resulting data is saved as an RDS file with a user-specified name suffix in a user-specified
#' directory. If the file already exists, the function loads the data from the file instead of retrieving it from
#' Google Trends. A sleep timer can also be specified to prevent exceeding Google's rate limits.
#'
#' @param sct A data frame with a column named "search_categories" and a column named "batch".
#' @param out_dir A string indicating the path to the directory where the output files will be saved.
#' @param suffix A string indicating the name suffix for the output files.
#' @param geo_code A string indicating the geographic code location for the Google Trends query.
#' @param sleep_time An optional numeric value indicating the number of seconds to sleep between Google Trends queries.
#' @param time_span A start and end date for the analysis of the trends
#'
#' @return A list of RDS files, one for each batch of search categories.
#'
#' @examples
#' batch_trends(sct = my_data, out_dir = "data/batch-search-us", suffix = "bsg", geo_code = "US", sleep_time = 3)
#'
#' @importFrom dplyr filter pull
#' @importFrom gtrendsR ts_gtrends
#' @importFrom lubridate format Sys.time
#' @importFrom utils dir.create file.exists saveRDS readRDS
#' @export
batch_trends <-
  function(sct,
           out_dir,
           suffix,
           geo_code,
           sleep_time = NULL,
           verbose=F,
           time_span) {
    # Check if necessary columns exist in the input data frame
    if (!("search_terms" %in% colnames(sct)) ||
        !("batch" %in% colnames(sct))) {
      stop("Input data frame must contain columns named 'search_categories' and 'batch'")
    }
    
    # Group the data by batch and retrieve Google Trends data for each batch
    lapply(0:max(sct$batch), function(x) {
      sct %>%
        dplyr::filter(batch == x) %>%
        pull(search_terms) %>%
        unique(.) -> keywords
      
      fname <- file.path(out_dir,
                         paste0(
                           suffix,
                           x,
                           "-",
                           format(Sys.time(), "%Y%m%d"),
                           "-",
                           suffix,
                           ".RDS"
                         ))
      
      if (!dir.exists(out_dir))
        dir.create(out_dir, recursive = TRUE)
      
      if (!file.exists(fname)) {
        # If sleep_time is not NULL, add a sleep timer between Google Trends queries
        if (!is.null(sleep_time)) {
          Sys.sleep(sleep_time)
        }
        if (verbose == T) {
          print(keywords)
        }
        ts_gtrends(keyword = keywords,
                   geo = geo_code,
                   time = time_span) -> g_data
        saveRDS(g_data, file = fname)
        
      } else {
        readRDS(fname) -> g_data
      }
      g_data
    }) %>% purrr::compact(.) %>% dplyr::bind_rows(.)
  }
