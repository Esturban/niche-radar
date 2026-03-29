#  Search Engine Marketing Analysis - SEM Analysis  

### An R project for evaluating Google Trends performance using single factor analysis in the `tidyverse`  

This R project implements a tidyverse approach to aggregating Google Trends results for various keywords generated into a single array relevant to a specific topic.   
> How do you determine the keywords and search terms which have performed well historically and are likely to continue with an uptrending trajectory?  

[Google Trends](https://trends.google.com/trends/explore "Google Trends") attempts to address the answer to a question like this, but limits you in the GUI to only look up 5 search terms at one time.
The SEM Analysis project uses a keywords extract from [Dashboardom](https://www.dashboardom.com/advertools) based on relevant combinations of the terms.  For more information on getting started with keyword generating, [this slide deck](https://www.slideshare.net/eliasdabbas/dont-research-keywords-generate-them) does a great job of explaining how best to maximize the use of the keyword generator.  

### Installation  

```sh
git clone https://github.com/Esturban/sem-analysis.git
```  

#### Dependencies  

The following are the required libraries to run the project:  

```r  
  pkgs <-
    c(
      'purrr',
      'dplyr',
      'tidyr',
      'magrittr',
      'reshape2',
      'gtrendsR',
      'GGally',
      'ggmap',
      'rvest'
    )
  
  invisible(suppressPackageStartupMessages(sapply(pkgs, require, character.only = T))) ->
    lib.out

c_lib_and_db <- ifelse(abs(sum(lib.out) - length(lib.out)), {
    tryCatch({
      install.packages(names(lib.out)[!lib.out], dependencies = T)
      return(T)
    }, error = function(err)
      F)
  }, T)  
  
```

### Limitations  

The following are the limitations of this project:  
- Daily limits may be reached for scaling of search terms on keyword extracts larger than 1000 observations 

### To do  

- Set limitations to the number of Google Trends calls the project can make on a daily basis  
- Build in a randomized sleep between Google Trends queries to extend the scale size
- Build in a unit test for evaluating that the adword_fn functions work as expected  


### Further Resources  

- [DataCamp Tutorial on Search Engine Marketing](http://bit.ly/datacamp_sem)  
- [DataCamp Project to practice generating keywords using Python and pands](https://www.datacamp.com/projects/400)  
- [Example use of the gtrendsR package](https://www.r-bloggers.com/vignette-google-trends-with-the-gtrendsr-package/)  
- [Using API-based R packages](http://lab.rady.ucsd.edu/sawtooth/business_analytics_in_r/DataApi.html)  


