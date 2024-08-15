object StringProcessor {
  def processStrings(strings: List[String]): List[String] = {
// здесь применение фильтра и мап последовательно
    strings.filter(_.length > 3).map(_.toUpperCase)
  }

  def main(args: Array[String]): Unit = {
    val strings = List("apple", "cat", "banana", "dog", "elephant")
    val processedStrings = processStrings(strings)
    println(s"Processed strings: $processedStrings")
  }
}
