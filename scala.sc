object StringProcessor {
  // Функция для обработки строк
  def processStrings(strings: List[String]): List[String] = {
    // Используем filter для выбора строк длиной более 3 символов и map для преобразования в верхний регистр
    strings.filter(_.length > 3).map(_.toUpperCase)
  }

  def main(args: Array[String]): Unit = {
    val strings = List("apple", "cat", "banana", "dog", "elephant")
    val processedStrings = processStrings(strings)
    println(s"Processed strings: $processedStrings")
  }
}
